"""Tests for deployment and release guardrails."""

from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]

BUILD_SPEC = importlib.util.spec_from_file_location(
    "hass_codex_usage_build_release",
    ROOT / "scripts" / "build_release.py",
)
build_release = importlib.util.module_from_spec(BUILD_SPEC)
assert BUILD_SPEC.loader is not None
BUILD_SPEC.loader.exec_module(build_release)

VALIDATE_SPEC = importlib.util.spec_from_file_location(
    "hass_codex_usage_validate",
    ROOT / "scripts" / "validate.py",
)
validate = importlib.util.module_from_spec(VALIDATE_SPEC)
assert VALIDATE_SPEC.loader is not None
VALIDATE_SPEC.loader.exec_module(validate)


class DeploymentTest(unittest.TestCase):
    """Test release packaging and deployment metadata."""

    def test_release_package_contains_runtime_files(self) -> None:
        """Package exactly the reviewed runtime allowlist."""
        package_files = {
            path.relative_to(build_release.INTEGRATION_DIR).as_posix()
            for path in build_release.validate_package_files()
        }
        required_files = {
            path.relative_to(build_release.INTEGRATION_DIR).as_posix()
            for path in build_release.REQUIRED_FILES
        }

        self.assertEqual(package_files, required_files)

    def test_release_package_rejects_unexpected_files(self) -> None:
        """Fail closed when an unreviewed file appears in the integration tree."""
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            integration_dir = Path(temporary) / "integration"
            integration_dir.mkdir()
            required = integration_dir / "runtime.py"
            required.write_text("# runtime\n", encoding="utf-8")
            (integration_dir / "scratch.txt").write_text("draft\n", encoding="utf-8")

            with (
                mock.patch.object(build_release, "INTEGRATION_DIR", integration_dir),
                mock.patch.object(build_release, "REQUIRED_FILES", (required,)),
                self.assertRaisesRegex(
                    build_release.ReleasePackageError,
                    "unexpected integration files: scratch.txt",
                ),
            ):
                build_release.validate_package_files()

    def test_release_package_rejects_sensitive_files(self) -> None:
        """Fail the build instead of silently ignoring a secret-like file."""
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            integration_dir = Path(temporary) / "integration"
            integration_dir.mkdir()
            required = integration_dir / "runtime.py"
            required.write_text("# runtime\n", encoding="utf-8")
            (integration_dir / ".env").write_text("TOKEN=secret\n", encoding="utf-8")

            with (
                mock.patch.object(build_release, "INTEGRATION_DIR", integration_dir),
                mock.patch.object(build_release, "REQUIRED_FILES", (required,)),
                self.assertRaisesRegex(
                    build_release.ReleasePackageError,
                    "refusing sensitive or generated file: .env",
                ),
            ):
                build_release.validate_package_files()

    def test_release_package_rejects_symlinked_files(self) -> None:
        """Do not archive content reached through a required-file symlink."""
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            temporary_path = Path(temporary)
            integration_dir = temporary_path / "integration"
            integration_dir.mkdir()
            outside_file = temporary_path / "outside.py"
            outside_file.write_text("SECRET = True\n", encoding="utf-8")
            required = integration_dir / "runtime.py"
            try:
                required.symlink_to(outside_file)
            except OSError as err:
                self.skipTest(f"symlinks are unavailable: {err}")

            with (
                mock.patch.object(build_release, "INTEGRATION_DIR", integration_dir),
                mock.patch.object(build_release, "REQUIRED_FILES", (required,)),
                self.assertRaisesRegex(
                    build_release.ReleasePackageError,
                    "refusing symlinked path: runtime.py",
                ),
            ):
                build_release.validate_package_files()

    def test_release_archive_uses_hacs_integration_root(self) -> None:
        """Extract the ZIP directly into the HACS integration destination."""
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            temporary_path = Path(temporary)
            output = temporary_path / "hass_codex_usage.zip"

            build_release.build_archive(output)

            with zipfile.ZipFile(output) as archive:
                names = set(archive.namelist())
                extract_dir = temporary_path / "custom_components" / "hass_codex_usage"
                archive.extractall(extract_dir)

            self.assertIn("manifest.json", names)
            self.assertIn("translations/en.json", names)
            self.assertNotIn("custom_components/hass_codex_usage/manifest.json", names)
            self.assertTrue((extract_dir / "manifest.json").is_file())
            self.assertFalse((extract_dir / "custom_components").exists())

    def test_release_archive_is_reproducible_across_file_mtimes(self) -> None:
        """Produce identical release bytes from identical source content."""
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            temporary_path = Path(temporary)
            integration_dir = temporary_path / "integration"
            integration_dir.mkdir()
            required = integration_dir / "runtime.py"
            required.write_text("VALUE = 1\n", encoding="utf-8")
            first_output = temporary_path / "first.zip"
            second_output = temporary_path / "second.zip"

            with (
                mock.patch.object(build_release, "INTEGRATION_DIR", integration_dir),
                mock.patch.object(build_release, "REQUIRED_FILES", (required,)),
            ):
                os.utime(required, (946684800, 946684800))
                build_release.build_archive(first_output)
                os.utime(required, (1767225600, 1767225600))
                build_release.build_archive(second_output)

            self.assertEqual(first_output.read_bytes(), second_output.read_bytes())

    def test_release_package_excludes_sensitive_or_generated_files(self) -> None:
        """Keep release artifacts free of local state and generated files."""
        package_files = [
            path.relative_to(build_release.INTEGRATION_DIR).as_posix()
            for path in build_release.validate_package_files()
        ]

        for relative in package_files:
            self.assertNotIn("__pycache__", relative)
            self.assertFalse(relative.endswith((".pyc", ".pyo", ".jsonl")))
            self.assertNotIn("token", relative.lower())
            self.assertNotIn("auth.json", relative.lower())

    def test_release_package_excludes_removed_parser_modules(self) -> None:
        """Do not restore the deleted compatibility parser modules."""
        package_files = {
            path.relative_to(build_release.INTEGRATION_DIR).as_posix()
            for path in build_release.validate_package_files()
        }
        self.assertTrue(
            {
                "usage_constants.py",
                "usage_extra.py",
                "usage_values.py",
                "usage_windows.py",
            }.isdisjoint(package_files)
        )

    def test_manifest_version_matches_code_version(self) -> None:
        """Keep Home Assistant manifest version aligned with sensor metadata."""
        manifest = json.loads(
            (ROOT / "custom_components" / "hass_codex_usage" / "manifest.json")
            .read_text(encoding="utf-8")
        )

        self.assertEqual(manifest["version"], validate.integration_version())

    def test_hacs_minimum_home_assistant_matches_runtime_apis(self) -> None:
        """Declare the first HA release supporting every API used at runtime."""
        hacs = json.loads((ROOT / "hacs.json").read_text(encoding="utf-8"))

        self.assertEqual(hacs["homeassistant"], "2025.12.0")

    def test_diagnostics_redact_identity_and_account_metadata(self) -> None:
        """Keep tokens and personally identifying account data out of diagnostics."""
        diagnostics_text = (
            ROOT / "custom_components" / "hass_codex_usage" / "diagnostics.py"
        ).read_text(encoding="utf-8")

        for key in (
            "access_token",
            "refresh_token",
            "id_token",
            "title",
            "unique_id",
            "account_email",
            "account_id",
        ):
            self.assertIn(f'"{key}"', diagnostics_text)

    def test_readme_manual_install_matches_archive_layout(self) -> None:
        """Describe extracting the root-level archive contents to the domain folder."""
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("`/config/custom_components/hass_codex_usage`", readme)
        self.assertNotIn(
            "Extract its `custom_components/hass_codex_usage` directory",
            readme,
        )


if __name__ == "__main__":
    unittest.main()

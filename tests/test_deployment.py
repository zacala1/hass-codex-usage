"""Tests for deployment and release guardrails."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD_RELEASE_PATH = ROOT / "scripts" / "build_release.py"
VALIDATE_PATH = ROOT / "scripts" / "validate.py"

BUILD_SPEC = importlib.util.spec_from_file_location(
    "hass_codex_usage_build_release",
    BUILD_RELEASE_PATH,
)
build_release = importlib.util.module_from_spec(BUILD_SPEC)
assert BUILD_SPEC.loader is not None
BUILD_SPEC.loader.exec_module(build_release)

VALIDATE_SPEC = importlib.util.spec_from_file_location(
    "hass_codex_usage_validate",
    VALIDATE_PATH,
)
validate = importlib.util.module_from_spec(VALIDATE_SPEC)
assert VALIDATE_SPEC.loader is not None
VALIDATE_SPEC.loader.exec_module(validate)


class DeploymentTest(unittest.TestCase):
    """Test release packaging and deployment metadata."""

    def test_release_package_contains_runtime_files(self) -> None:
        """Include every runtime file needed after HACS or manual install."""
        package_files = {
            path.relative_to(build_release.INTEGRATION_DIR).as_posix()
            for path in build_release.validate_package_files()
        }

        for required in build_release.REQUIRED_FILES:
            relative = required.relative_to(build_release.INTEGRATION_DIR).as_posix()
            self.assertIn(relative, package_files)

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

    def test_release_workflow_runs_validation_before_packaging(self) -> None:
        """Avoid publishing a release artifact that skipped local validation."""
        self.assertEqual(validate.check_workflows(), [])


if __name__ == "__main__":
    unittest.main()

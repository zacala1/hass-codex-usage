"""Tests for the release tag validation command."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    ROOT / "custom_components" / "hass_codex_usage" / "manifest.json"
)
SCRIPT_PATH = ROOT / "scripts" / "check_release_tag.py"
SCRIPT_SPEC = importlib.util.spec_from_file_location(
    "hass_codex_usage_check_release_tag", SCRIPT_PATH
)
check_release_tag = importlib.util.module_from_spec(SCRIPT_SPEC)
assert SCRIPT_SPEC.loader is not None
SCRIPT_SPEC.loader.exec_module(check_release_tag)


class ReleaseTagTest(unittest.TestCase):
    """Test release tag and manifest version alignment."""

    def test_release_tag_must_match_manifest_version(self) -> None:
        """Reject a pushed release tag that differs from the manifest version."""
        # Given: the version currently declared by the integration manifest.
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        accepted_tag = f"v{manifest['version']}"

        # When: matching and non-matching tags are validated.
        accepted = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), accepted_tag],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        rejected = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), f"{accepted_tag}-mismatch"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        # Then: only the manifest-derived tag is accepted.
        self.assertEqual(accepted.returncode, 0, accepted.stderr)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("does not match manifest version", rejected.stderr)

    def test_beta_versions_are_classified_as_prereleases(self) -> None:
        """Classify beta tags without marking the final version as prerelease."""
        self.assertTrue(check_release_tag.release_is_prerelease("0.3.2b1"))
        self.assertTrue(check_release_tag.release_is_prerelease("0.3.2rc1"))
        self.assertFalse(check_release_tag.release_is_prerelease("0.3.2"))
        self.assertFalse(check_release_tag.release_is_prerelease("previewb1"))

    def test_github_output_reports_current_beta_release_type(self) -> None:
        """Expose release type for the GitHub release publishing action."""
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        accepted_tag = f"v{manifest['version']}"

        with tempfile.TemporaryDirectory() as temporary:
            output_path = Path(temporary) / "github-output.txt"
            environment = {**os.environ, "GITHUB_OUTPUT": str(output_path)}
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--github-output",
                    accepted_tag,
                ],
                cwd=ROOT,
                env=environment,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "prerelease=true\n",
            )

    def test_release_workflow_preserves_the_beta_channel(self) -> None:
        """Publish beta tags as prereleases instead of replacing Latest."""
        release_text = (
            ROOT / ".github" / "workflows" / "release.yml"
        ).read_text(encoding="utf-8")

        self.assertIn("id: release_metadata", release_text)
        self.assertIn(
            "prerelease: ${{ steps.release_metadata.outputs.prerelease }}",
            release_text,
        )


if __name__ == "__main__":
    unittest.main()

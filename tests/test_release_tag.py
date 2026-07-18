"""Tests for the release tag validation command."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    ROOT / "custom_components" / "hass_codex_usage" / "manifest.json"
)
SCRIPT_PATH = ROOT / "scripts" / "check_release_tag.py"


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


if __name__ == "__main__":
    unittest.main()

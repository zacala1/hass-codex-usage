"""Tests for current public documentation contracts."""

from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README_PATH = ROOT / "README.md"


class DocumentationTest(unittest.TestCase):
    """Keep README guidance aligned with current integration behavior."""

    def test_usage_window_classification_is_documented(self) -> None:
        """Explain how session and weekly windows are identified."""
        # Given: the public README.
        readme = README_PATH.read_text(encoding="utf-8")

        # When: its sensor semantics are read.
        sensor_section = readme.split("## Sensors", maxsplit=1)[-1]

        # Then: duration-based five-hour and seven-day classification is explicit.
        self.assertIn("`limit_window_seconds`", sensor_section)
        self.assertIn("five-hour", sensor_section)
        self.assertIn("seven-day", sensor_section)

    def test_unavailable_optional_limits_are_documented(self) -> None:
        """Explain why optional sensors can legitimately be unavailable."""
        # Given: the public README.
        readme = README_PATH.read_text(encoding="utf-8")

        # When: optional-limit guidance is read.
        sensor_section = readme.split("## Sensors", maxsplit=1)[-1]

        # Then: both backend objects and the visible Unknown state are explained.
        self.assertIn("`spend_control.individual_limit`", sensor_section)
        self.assertIn("`codex_auto_review`", sensor_section)
        self.assertIn("Unknown", sensor_section)

    def test_localized_update_and_release_guidance_is_current(self) -> None:
        """Keep Korean support, HACS refresh, and release tags current."""
        # Given: the public README after the v0.3.1 behavior update.
        readme = README_PATH.read_text(encoding="utf-8")

        # When: user and maintainer guidance is inspected.
        normalized = readme.lower()

        # Then: localized UI, full HACS update steps, and generic tags are covered.
        self.assertIn("한국어", readme)
        self.assertIn("**Update information**", readme)
        self.assertIn("Download/Redownload", readme)
        self.assertIn("restart Home Assistant", readme)
        self.assertIn("`v<manifest version>`", readme)
        self.assertNotIn("v0.3.0", normalized)

    def test_english_copy_and_current_fixed_fields_are_documented(self) -> None:
        """Keep public English natural and document current fixed coverage."""
        readme = README_PATH.read_text(encoding="utf-8")

        self.assertNotIn("offered update", readme)
        self.assertNotIn("English and 한국어", readme)
        self.assertNotIn("The integration identifies the approximately", readme)
        self.assertIn("rate-limit reset credits", readme.lower())
        self.assertIn("`rate_limit_reached_type`", readme)


if __name__ == "__main__":
    unittest.main()

"""Tests for Home Assistant translation metadata."""

from __future__ import annotations

import json
import importlib.util
import re
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TRANSLATION_FILES = (
    ROOT / "custom_components" / "hass_codex_usage" / "strings.json",
    ROOT / "custom_components" / "hass_codex_usage" / "translations" / "en.json",
    ROOT / "custom_components" / "hass_codex_usage" / "translations" / "ko.json",
)
USAGE_PATH = ROOT / "custom_components" / "hass_codex_usage" / "usage.py"
USAGE_SPEC = importlib.util.spec_from_file_location("translation_usage", USAGE_PATH)
assert USAGE_SPEC is not None and USAGE_SPEC.loader is not None
usage = importlib.util.module_from_spec(USAGE_SPEC)
USAGE_SPEC.loader.exec_module(usage)
PLACEHOLDER_RE = re.compile(r"{([A-Za-z_][A-Za-z0-9_]*)}")


class TranslationTest(unittest.TestCase):
    """Test translation files used by the config flow."""

    def test_oauth_descriptions_use_supported_link_placeholder(self) -> None:
        """Keep OAuth link copy aligned with config-flow placeholders."""
        for path, data in self._translation_data():
            with self.subTest(path=path.name):
                steps = data["config"]["step"]
                for step_id in ("user", "reauth_confirm"):
                    description = steps[step_id]["description"]
                    placeholders = set(PLACEHOLDER_RE.findall(description))

                    self.assertIn("url", placeholders)
                    self.assertIn("[open link]({url})", description)
                    self.assertNotIn("auth_url", placeholders)
                    self.assertLessEqual(placeholders, {"url"})

    def test_oauth_steps_keep_single_paste_field(self) -> None:
        """Keep setup close to the single-form hass-claude-usage pattern."""
        for path, data in self._translation_data():
            with self.subTest(path=path.name):
                steps = data["config"]["step"]

                self.assertNotIn("auth_code", steps)
                self.assertNotIn("device_auth", steps)
                self.assertNotIn("menu_options", steps["user"])
                self.assertEqual(
                    set(steps["user"]["data"]),
                    {"authorization_code"},
                )
                self.assertEqual(
                    set(steps["reauth_confirm"]["data"]),
                    {"authorization_code"},
                )

    def test_sensor_translations_match_current_sensor_set(self) -> None:
        """Keep all translation files on the exact current sensor contract."""
        for path, data in self._translation_data():
            with self.subTest(path=path.name):
                self.assertEqual(
                    set(data["entity"]["sensor"]), set(usage.SENSOR_KEYS)
                )

    @staticmethod
    def _translation_data() -> list[tuple[Path, dict[str, Any]]]:
        """Load translation files."""
        return [
            (path, json.loads(path.read_text(encoding="utf-8")))
            for path in TRANSLATION_FILES
        ]


if __name__ == "__main__":
    unittest.main()

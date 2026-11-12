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
ENGLISH_TRANSLATION_FILES = TRANSLATION_FILES[:2]
USAGE_PATH = ROOT / "custom_components" / "hass_codex_usage" / "usage.py"
USAGE_SPEC = importlib.util.spec_from_file_location("translation_usage", USAGE_PATH)
assert USAGE_SPEC is not None and USAGE_SPEC.loader is not None
usage = importlib.util.module_from_spec(USAGE_SPEC)
USAGE_SPEC.loader.exec_module(usage)
PLACEHOLDER_RE = re.compile(r"{([A-Za-z_][A-Za-z0-9_]*)}")
MARKDOWN_URL_LINK_RE = re.compile(r"\[[^\]]+\]\(\{url\}\)")


class TranslationTest(unittest.TestCase):
    """Test translation files used by the config flow."""

    def test_oauth_descriptions_use_supported_link_placeholder(self) -> None:
        """Keep OAuth link copy aligned with config-flow placeholders."""
        # Given: every localized config-flow description.
        for path, data in self._translation_data():
            with self.subTest(path=path.name):
                steps = data["config"]["step"]
                for step_id in ("user", "reauth_confirm"):
                    # When: its placeholders and Markdown link are inspected.
                    description = steps[step_id]["description"]
                    placeholders = set(PLACEHOLDER_RE.findall(description))

                    # Then: localized link text may vary, but its URL contract cannot.
                    self.assertIn("url", placeholders)
                    self.assertRegex(description, MARKDOWN_URL_LINK_RE)
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
        """Keep English translation files on the exact current sensor contract."""
        for path in ENGLISH_TRANSLATION_FILES:
            with self.subTest(path=path.name):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(
                    set(data["entity"]["sensor"]), set(usage.SENSOR_KEYS)
                )

    def test_korean_copy_localizes_setup_but_not_assigned_names(self) -> None:
        """Keep Korean guidance while entity names fall back to English."""
        # Given: the Korean custom-integration translation file.
        korean = json.loads(TRANSLATION_FILES[2].read_text(encoding="utf-8"))

        # When: setup guidance and integration-assigned names are inspected.
        user_step = korean["config"]["step"]["user"]

        # Then: setup remains Korean and assigned names have no Korean override.
        self.assertIn("[인증 페이지 열기]({url})", user_step["description"])
        self.assertIn(
            "다시 인증",
            korean["config"]["step"]["reauth_confirm"]["description"],
        )
        self.assertIn(
            "연결할 수 없습니다",
            korean["config"]["error"]["cannot_connect"],
        )
        self.assertEqual(
            korean["options"]["step"]["init"]["title"],
            "Codex 사용량 설정",
        )
        self.assertEqual(korean["title"], "Codex Usage")
        self.assertNotIn("entity", korean)

    def test_english_copy_is_native_and_unambiguous(self) -> None:
        """Use natural English that names each measured quantity."""
        strings = json.loads(TRANSLATION_FILES[0].read_text(encoding="utf-8"))
        english = json.loads(TRANSLATION_FILES[1].read_text(encoding="utf-8"))

        self.assertEqual(strings, english)
        self.assertIn(
            "[Open the authentication page]({url})",
            english["config"]["step"]["user"]["description"],
        )
        self.assertEqual(
            english["entity"]["sensor"]["session_usage_remaining"]["name"],
            "Session usage remaining",
        )
        self.assertEqual(
            english["entity"]["sensor"]["weekly_usage_remaining"]["name"],
            "Weekly usage remaining",
        )
        self.assertEqual(
            english["entity"]["sensor"]["extra_usage_used"]["name"],
            "Extra credits used",
        )
        self.assertEqual(
            english["entity"]["sensor"][
                "rate_limit_reset_credits_available"
            ]["name"],
            "Available rate limit reset credits",
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

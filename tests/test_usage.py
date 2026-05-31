"""Tests for Codex usage response parsing."""

from __future__ import annotations

import importlib.util
import unittest
from datetime import timezone
from pathlib import Path

USAGE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "hass_codex_usage"
    / "usage.py"
)
SPEC = importlib.util.spec_from_file_location("hass_codex_usage_usage", USAGE_PATH)
usage = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(usage)


class UsageParsingTest(unittest.TestCase):
    """Test usage response parsing."""

    def test_planned_schema(self) -> None:
        """Parse the v0.1 planned response shape."""
        payload = {
            "plan": "plus",
            "rate_limits": {
                "primary_window": {
                    "used_percent": 39.2,
                    "reset_at": "2026-05-31T15:30:00Z",
                },
                "secondary_window": {
                    "used_percent": 15,
                    "reset_at": "2026-06-06T08:00:00Z",
                },
                "code_review_rate_limit": {
                    "used_percent": 0,
                    "reset_at": "2026-05-31T18:00:00Z",
                },
            },
        }

        self.assertEqual(usage.sensor_value(payload, usage.PLAN), "plus")
        self.assertEqual(usage.sensor_value(payload, usage.SESSION_USAGE), 39.2)
        self.assertEqual(usage.sensor_value(payload, usage.WEEKLY_USAGE), 15)
        self.assertEqual(usage.sensor_value(payload, usage.CODE_REVIEW_USAGE), 0)
        self.assertEqual(
            usage.sensor_value(payload, usage.SESSION_RESET_TIME).isoformat(),
            "2026-05-31T15:30:00+00:00",
        )
        self.assertEqual(
            usage.sensor_value(payload, usage.WEEKLY_RESET_TIME).isoformat(),
            "2026-06-06T08:00:00+00:00",
        )
        self.assertEqual(
            usage.sensor_value(payload, usage.CODE_REVIEW_RESET_TIME).isoformat(),
            "2026-05-31T18:00:00+00:00",
        )

    def test_alternate_field_names(self) -> None:
        """Parse conservative alternate names seen in similar payloads."""
        payload = {
            "chatgpt_plan_type": "pro",
            "usage": {
                "primary_window": {
                    "usage_percent": 51,
                    "resets_at": "2026-05-31T15:30:00+09:00",
                },
                "secondary_window": {
                    "percent_used": 12.5,
                    "reset_time": "2026-06-06T08:00:00",
                },
            },
            "rate_limits": {
                "code_review": {
                    "usage_percent": 4,
                    "resets_at": "2026-05-31T18:00:00Z",
                },
            },
        }

        self.assertEqual(usage.sensor_value(payload, usage.PLAN), "pro")
        self.assertEqual(usage.sensor_value(payload, usage.SESSION_USAGE), 51)
        self.assertEqual(usage.sensor_value(payload, usage.WEEKLY_USAGE), 12.5)
        self.assertEqual(usage.sensor_value(payload, usage.CODE_REVIEW_USAGE), 4)
        self.assertEqual(
            usage.sensor_value(payload, usage.SESSION_RESET_TIME).isoformat(),
            "2026-05-31T15:30:00+09:00",
        )
        self.assertEqual(
            usage.sensor_value(payload, usage.WEEKLY_RESET_TIME).tzinfo,
            timezone.utc,
        )

    def test_missing_or_invalid_values_return_none(self) -> None:
        """Return None for unavailable values instead of raising."""
        payload = {
            "rate_limits": {
                "primary_window": {
                    "used_percent": True,
                    "reset_at": "not-a-date",
                }
            }
        }

        self.assertIsNone(usage.sensor_value(payload, usage.SESSION_USAGE))
        self.assertIsNone(usage.sensor_value(payload, usage.SESSION_RESET_TIME))
        self.assertIsNone(usage.sensor_value(payload, usage.WEEKLY_USAGE))
        self.assertIsNone(usage.sensor_value(payload, usage.WEEKLY_RESET_TIME))
        self.assertIsNone(usage.sensor_value(payload, usage.PLAN))

    def test_parse_timestamp(self) -> None:
        """Parse Z, offset, and naive timestamps."""
        self.assertEqual(
            usage.parse_timestamp("2026-05-31T15:30:00Z").isoformat(),
            "2026-05-31T15:30:00+00:00",
        )
        self.assertEqual(
            usage.parse_timestamp("2026-05-31T15:30:00+09:00").isoformat(),
            "2026-05-31T15:30:00+09:00",
        )
        self.assertEqual(
            usage.parse_timestamp("2026-05-31T15:30:00").tzinfo,
            timezone.utc,
        )
        self.assertIsNone(usage.parse_timestamp(""))
        self.assertIsNone(usage.parse_timestamp(None))


if __name__ == "__main__":
    unittest.main()

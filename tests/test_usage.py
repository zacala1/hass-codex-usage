"""Tests for the current Codex usage response parser."""

from __future__ import annotations

from datetime import timezone
import importlib.util
from pathlib import Path
import unittest

USAGE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "hass_codex_usage"
    / "usage.py"
)
SPEC = importlib.util.spec_from_file_location("hass_codex_usage_usage", USAGE_PATH)
assert SPEC is not None and SPEC.loader is not None
usage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(usage)


class UsageParsingTest(unittest.TestCase):
    """Test current-schema usage parsing."""

    def test_remaining_sensor_keys_include_usage(self) -> None:
        """Name remaining sensors as scope usage remaining."""
        self.assertIn("session_usage_remaining", usage.SENSOR_KEYS)
        self.assertIn("weekly_usage_remaining", usage.SENSOR_KEYS)
        self.assertIn("code_review_usage_remaining", usage.SENSOR_KEYS)
        self.assertNotIn("session_remaining", usage.SENSOR_KEYS)
        self.assertNotIn("weekly_remaining", usage.SENSOR_KEYS)
        self.assertNotIn("code_review_remaining", usage.SENSOR_KEYS)

    def test_subscription_windows_report_remaining_percent(self) -> None:
        payload = {
            "plan_type": "plus",
            "rate_limit": {
                "allowed": True,
                "limit_reached": False,
                "primary_window": {
                    "used_percent": 73.5,
                    "limit_window_seconds": 18000,
                    "reset_after_seconds": 900,
                    "reset_at": 0,
                },
                "secondary_window": {
                    "used_percent": 54,
                    "reset_at": 1784937600,
                },
            },
        }

        self.assertEqual(usage.sensor_value(payload, usage.PLAN), "plus")
        self.assertEqual(
            usage.sensor_value(payload, usage.SESSION_USAGE_REMAINING), 26.5
        )
        self.assertEqual(
            usage.sensor_value(payload, usage.WEEKLY_USAGE_REMAINING), 46
        )
        self.assertEqual(
            usage.sensor_value(payload, usage.SESSION_RESET_TIME).isoformat(),
            "1970-01-01T00:00:00+00:00",
        )
        self.assertEqual(
            usage.sensor_attributes(payload, usage.SESSION_USAGE_REMAINING),
            {
                "allowed": True,
                "limit_reached": False,
                "limit_window_seconds": 18000,
                "reset_after_seconds": 900,
            },
        )

    def test_windows_are_classified_by_duration_not_position(self) -> None:
        # Given: the API puts the weekly limit first and the five-hour limit second.
        payload = {
            "rate_limit": {
                "primary_window": {
                    "used_percent": 94,
                    "limit_window_seconds": 7 * 24 * 60 * 60,
                },
                "secondary_window": {
                    "used_percent": 40,
                    "limit_window_seconds": 5 * 60 * 60,
                },
            }
        }

        # When: both fixed sensor values are parsed.
        values = (
            usage.sensor_value(payload, usage.SESSION_USAGE_REMAINING),
            usage.sensor_value(payload, usage.WEEKLY_USAGE_REMAINING),
        )

        # Then: duration, rather than primary/secondary position, selects them.
        self.assertEqual(values, (60, 6))

    def test_weekly_only_primary_window_is_not_reported_as_session(self) -> None:
        # Given: the account receives only one seven-day window in primary position.
        payload = {
            "rate_limit": {
                "primary_window": {
                    "used_percent": 25,
                    "limit_window_seconds": 7 * 24 * 60 * 60,
                    "reset_at": 1784937600,
                }
            }
        }

        # When: session and weekly values are parsed.
        values = (
            usage.sensor_value(payload, usage.SESSION_USAGE_REMAINING),
            usage.sensor_value(payload, usage.WEEKLY_USAGE_REMAINING),
            usage.sensor_value(payload, usage.SESSION_RESET_TIME),
            usage.sensor_value(payload, usage.WEEKLY_RESET_TIME),
        )

        # Then: the weekly value is shown once and session remains unavailable.
        self.assertEqual(
            values,
            (None, 75, None, usage.parse_timestamp(1784937600)),
        )

    def test_code_review_uses_exact_current_feature_name(self) -> None:
        payload = {
            "additional_rate_limits": [
                {
                    "metered_feature": "code_review",
                    "rate_limit": {"primary_window": {"used_percent": 1}},
                },
                {
                    "metered_feature": "codex_auto_review",
                    "limit_name": "Code review weekly",
                    "rate_limit": {
                        "allowed": True,
                        "limit_reached": False,
                        "primary_window": {
                            "used_percent": 9,
                            "reset_at": 7200,
                        },
                    },
                },
            ]
        }

        self.assertEqual(
            usage.sensor_value(payload, usage.CODE_REVIEW_USAGE_REMAINING), 91
        )
        self.assertEqual(
            usage.sensor_attributes(payload, usage.CODE_REVIEW_USAGE_REMAINING),
            {
                "allowed": True,
                "limit_reached": False,
                "metered_feature": "codex_auto_review",
                "limit_name": "Code review weekly",
            },
        )

    def test_extra_usage_uses_individual_limit_and_credit_balance(self) -> None:
        payload = {
            "credits": {
                "has_credits": True,
                "unlimited": False,
                "balance": "42.5",
            },
            "spend_control": {
                "reached": False,
                "individual_limit": {
                    "source": "monthly",
                    "limit": "100",
                    "used": "35",
                    "remaining": "65",
                    "used_percent": 35,
                    "remaining_percent": 61,
                    "reset_after_seconds": 60,
                    "reset_at": 1785542400,
                },
            },
        }

        self.assertEqual(
            usage.sensor_value(payload, usage.EXTRA_USAGE_REMAINING), 61
        )
        self.assertEqual(usage.sensor_value(payload, usage.EXTRA_USAGE_USED), 35)
        self.assertEqual(usage.sensor_value(payload, usage.EXTRA_USAGE_LIMIT), 100)
        self.assertEqual(
            usage.sensor_value(payload, usage.EXTRA_USAGE_BALANCE), 42.5
        )
        self.assertEqual(
            usage.sensor_value(payload, usage.EXTRA_USAGE_RESET_TIME).isoformat(),
            "2026-08-01T00:00:00+00:00",
        )
        self.assertEqual(
            usage.sensor_attributes(payload, usage.EXTRA_USAGE_BALANCE),
            {"has_credits": True, "unlimited": False, "balance": "42.5"},
        )

    def test_missing_invalid_and_nonfinite_values_return_none(self) -> None:
        payload = {
            "plan": "legacy",
            "rate_limits": {"primary_window": {"used_percent": 10}},
            "rate_limit": {
                "primary_window": {
                    "used_percent": float("nan"),
                    "reset_at": "not-a-date",
                }
            },
            "spend_control": {
                "individual_limit": {"remaining_percent": float("inf")}
            },
        }

        self.assertIsNone(usage.sensor_value(payload, usage.PLAN))
        self.assertIsNone(
            usage.sensor_value(payload, usage.SESSION_USAGE_REMAINING)
        )
        self.assertIsNone(usage.sensor_value(payload, usage.SESSION_RESET_TIME))
        self.assertIsNone(
            usage.sensor_value(payload, usage.EXTRA_USAGE_REMAINING)
        )

    def test_only_current_string_numeric_fields_accept_strings(self) -> None:
        payload = {
            "rate_limit": {
                "primary_window": {
                    "used_percent": "10",
                    "reset_at": "1785542400",
                }
            },
            "credits": {"balance": "20"},
            "spend_control": {
                "individual_limit": {
                    "remaining_percent": "50",
                    "used": "10",
                    "limit": "100",
                }
            },
        }

        self.assertIsNone(
            usage.sensor_value(payload, usage.SESSION_USAGE_REMAINING)
        )
        self.assertIsNone(usage.sensor_value(payload, usage.SESSION_RESET_TIME))
        self.assertEqual(usage.sensor_value(payload, usage.EXTRA_USAGE_BALANCE), 20)
        self.assertIsNone(
            usage.sensor_value(payload, usage.EXTRA_USAGE_REMAINING)
        )
        self.assertEqual(usage.sensor_value(payload, usage.EXTRA_USAGE_USED), 10)
        self.assertEqual(usage.sensor_value(payload, usage.EXTRA_USAGE_LIMIT), 100)

    def test_percentages_are_clamped(self) -> None:
        self.assertEqual(
            usage.sensor_value(
                {"rate_limit": {"primary_window": {"used_percent": 130}}},
                usage.SESSION_USAGE_REMAINING,
            ),
            0,
        )
        self.assertEqual(
            usage.sensor_value(
                {
                    "spend_control": {
                        "individual_limit": {"remaining_percent": 120}
                    }
                },
                usage.EXTRA_USAGE_REMAINING,
            ),
            100,
        )

    def test_parse_timestamp(self) -> None:
        self.assertEqual(usage.parse_timestamp(0).tzinfo, timezone.utc)
        self.assertIsNone(usage.parse_timestamp(""))
        self.assertIsNone(usage.parse_timestamp("2026-07-18T15:30:00Z"))
        self.assertIsNone(usage.parse_timestamp(True))


if __name__ == "__main__":
    unittest.main()

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
            "_meta": {
                "account_email": "user@example.com",
                "api_endpoint": "chatgpt.com/backend-api/wham/usage",
            },
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

    def test_current_codex_rate_limit_shape(self) -> None:
        """Parse the rate-limit shape used by the current Codex backend client."""
        payload = {
            "plan_type": "plus",
            "credits": {
                "used_credits": 125,
                "remaining_credits": 375,
                "monthly_limit": 500,
            },
            "spend_control": {
                "is_enabled": True,
                "auto_top_up_enabled": False,
            },
            "rate_limit": {
                "primary_window": {
                    "used_percent": 73.5,
                    "limit_window_seconds": 18000,
                    "reset_after_seconds": 900,
                    "allowed": True,
                    "limit_reached": False,
                    "reset_at": 0,
                },
                "secondary_window": {
                    "used_percent": 54,
                    "limit_window_seconds": 604800,
                    "reset_at": 3600,
                },
            },
            "additional_rate_limits": [
                {
                    "metered_feature": "code_review",
                    "limit_name": "Code review Weekly",
                    "rate_limit": {
                        "primary_window": {
                            "used_percent": 9,
                            "limit_window_seconds": 604800,
                            "reset_after_seconds": 1200,
                            "reset_at": 7200,
                        }
                    },
                }
            ],
        }

        self.assertEqual(usage.sensor_value(payload, usage.PLAN), "plus")
        self.assertEqual(usage.sensor_value(payload, usage.SESSION_USAGE), 73.5)
        self.assertEqual(usage.sensor_value(payload, usage.WEEKLY_USAGE), 54)
        self.assertEqual(usage.sensor_value(payload, usage.CODE_REVIEW_USAGE), 9)
        self.assertIs(usage.sensor_value(payload, usage.EXTRA_USAGE_ENABLED), True)
        self.assertEqual(usage.sensor_value(payload, usage.EXTRA_USAGE), 25)
        self.assertEqual(usage.sensor_value(payload, usage.EXTRA_USAGE_CREDITS), 125)
        self.assertEqual(usage.sensor_value(payload, usage.EXTRA_USAGE_LIMIT), 500)
        self.assertEqual(
            usage.sensor_value(payload, usage.SESSION_RESET_TIME).isoformat(),
            "1970-01-01T00:00:00+00:00",
        )
        self.assertEqual(
            usage.sensor_value(payload, usage.WEEKLY_RESET_TIME).isoformat(),
            "1970-01-01T01:00:00+00:00",
        )
        self.assertEqual(
            usage.sensor_value(payload, usage.CODE_REVIEW_RESET_TIME).isoformat(),
            "1970-01-01T02:00:00+00:00",
        )
        self.assertEqual(
            usage.sensor_attributes(payload, usage.SESSION_USAGE),
            {
                "allowed": True,
                "limit_reached": False,
                "limit_window_seconds": 18000,
                "reset_after_seconds": 900,
            },
        )
        self.assertEqual(
            usage.sensor_attributes(payload, usage.CODE_REVIEW_USAGE),
            {
                "limit_window_seconds": 604800,
                "reset_after_seconds": 1200,
                "metered_feature": "code_review",
                "limit_name": "Code review Weekly",
            },
        )
        self.assertEqual(
            usage.sensor_attributes(payload, usage.EXTRA_USAGE),
            {
                "auto_top_up_enabled": False,
                "remaining_credits": 375,
                "used_credits": 125,
                "monthly_limit": 500,
            },
        )

    def test_extra_usage_from_additional_rate_limits(self) -> None:
        """Parse flexible-usage credits from additional rate limit entries."""
        payload = {
            "additional_rate_limits": [
                {
                    "metered_feature": "codex_flexible_usage",
                    "limit_name": "Flexible usage credits",
                    "credits": {
                        "credit_balance": 42,
                    },
                    "spend_control": {
                        "enabled": True,
                        "limit": 100,
                    },
                    "rate_limit": {
                        "primary_window": {
                            "used_percent": 12,
                        },
                    },
                }
            ]
        }

        self.assertIs(usage.sensor_value(payload, usage.EXTRA_USAGE_ENABLED), True)
        self.assertEqual(usage.sensor_value(payload, usage.EXTRA_USAGE), 12)
        self.assertEqual(usage.sensor_value(payload, usage.EXTRA_USAGE_CREDITS), 42)
        self.assertEqual(usage.sensor_value(payload, usage.EXTRA_USAGE_LIMIT), 100)
        self.assertEqual(
            usage.sensor_attributes(payload, usage.EXTRA_USAGE_CREDITS),
            {
                "metered_feature": "codex_flexible_usage",
                "limit_name": "Flexible usage credits",
                "credit_balance": 42,
                "limit": 100,
            },
        )

    def test_codex_credit_balance_string_shape(self) -> None:
        """Parse the Codex credits shape used by open-source usage checkers."""
        payload = {
            "plan_type": "prolite",
            "credits": {
                "has_credits": False,
                "unlimited": False,
                "balance": "0",
            },
            "spend_control": {
                "reached": False,
            },
        }

        self.assertIs(usage.sensor_value(payload, usage.EXTRA_USAGE_ENABLED), False)
        self.assertEqual(usage.sensor_value(payload, usage.EXTRA_USAGE), 0)
        self.assertEqual(usage.sensor_value(payload, usage.EXTRA_USAGE_CREDITS), 0)
        self.assertEqual(usage.sensor_value(payload, usage.EXTRA_USAGE_LIMIT), 0)
        self.assertEqual(
            usage.sensor_attributes(payload, usage.EXTRA_USAGE_CREDITS),
            {
                "has_credits": False,
                "unlimited": False,
                "balance": "0",
                "reached": False,
            },
        )

    def test_optional_sensors_require_backing_data(self) -> None:
        """Do not expose optional sensors when the endpoint omits their data."""
        payload = {
            "plan_type": "prolite",
            "rate_limit": {
                "primary_window": {
                    "used_percent": 1,
                    "reset_at": 0,
                },
                "secondary_window": {
                    "used_percent": 40,
                    "reset_at": 3600,
                },
            },
        }

        self.assertTrue(usage.sensor_supported(payload, usage.SESSION_USAGE))
        self.assertTrue(usage.sensor_supported(payload, usage.WEEKLY_USAGE))
        self.assertFalse(usage.sensor_supported(payload, usage.EXTRA_USAGE))
        self.assertFalse(usage.sensor_supported(payload, usage.EXTRA_USAGE_LIMIT))
        self.assertFalse(usage.sensor_supported(payload, usage.CODE_REVIEW_USAGE))
        self.assertFalse(
            usage.sensor_supported(payload, usage.CODE_REVIEW_RESET_TIME)
        )
        self.assertFalse(usage.sensor_supported(payload, usage.CODEX_SPARK_USAGE))

    def test_codex_positive_credit_balance_enables_extra_usage(self) -> None:
        """Parse a positive Codex credit balance returned as a string."""
        payload = {
            "credits": {
                "has_credits": True,
                "unlimited": False,
                "balance": "45.25",
            },
            "spend_control": {
                "reached": False,
            },
        }

        self.assertIs(usage.sensor_value(payload, usage.EXTRA_USAGE_ENABLED), True)
        self.assertEqual(usage.sensor_value(payload, usage.EXTRA_USAGE_CREDITS), 45.25)
        self.assertIsNone(usage.sensor_value(payload, usage.EXTRA_USAGE))

    def test_extra_usage_percent_from_remaining_and_limit(self) -> None:
        """Derive extra usage percent from remaining credits and a total limit."""
        payload = {
            "billing": {
                "credits": {
                    "remaining": "75",
                    "limit": "100",
                }
            }
        }

        self.assertIs(usage.sensor_value(payload, usage.EXTRA_USAGE_ENABLED), True)
        self.assertEqual(usage.sensor_value(payload, usage.EXTRA_USAGE), 25)
        self.assertEqual(usage.sensor_value(payload, usage.EXTRA_USAGE_CREDITS), 75)
        self.assertEqual(usage.sensor_value(payload, usage.EXTRA_USAGE_LIMIT), 100)

    def test_codex_spark_from_additional_rate_limits(self) -> None:
        """Parse Codex Spark windows from additional rate limit entries."""
        payload = {
            "additional_rate_limits": [
                {
                    "limit_name": "GPT-5.3-Codex-Spark",
                    "metered_feature": "gpt_5_3_codex_spark",
                    "rate_limit": {
                        "allowed": True,
                        "limit_reached": False,
                        "primary_window": {
                            "used_percent": 30,
                            "reset_at": 0,
                            "limit_window_seconds": 18000,
                            "reset_after_seconds": 12345,
                        },
                        "secondary_window": {
                            "used_percent": 100,
                            "reset_at": 3600,
                            "limit_window_seconds": 604800,
                        },
                    },
                }
            ]
        }

        self.assertEqual(usage.sensor_value(payload, usage.CODEX_SPARK_USAGE), 30)
        self.assertEqual(
            usage.sensor_value(payload, usage.CODEX_SPARK_RESET_TIME).isoformat(),
            "1970-01-01T00:00:00+00:00",
        )
        self.assertEqual(
            usage.sensor_value(payload, usage.CODEX_SPARK_WEEKLY_USAGE),
            100,
        )
        self.assertEqual(
            usage.sensor_value(
                payload,
                usage.CODEX_SPARK_WEEKLY_RESET_TIME,
            ).isoformat(),
            "1970-01-01T01:00:00+00:00",
        )
        self.assertEqual(
            usage.sensor_attributes(payload, usage.CODEX_SPARK_USAGE),
            {
                "allowed": True,
                "limit_reached": False,
                "limit_window_seconds": 18000,
                "reset_after_seconds": 12345,
                "metered_feature": "gpt_5_3_codex_spark",
                "limit_name": "GPT-5.3-Codex-Spark",
            },
        )

    def test_code_review_label_variants(self) -> None:
        """Parse code-review limits with current dashboard/API label variants."""
        payload = {
            "additional_rate_limits": [
                {
                    "metered_feature": "github_code_review",
                    "rate_limit": {
                        "primary_window": {
                            "used_percent": 99,
                        }
                    },
                },
                {
                    "limit_name": "Core review",
                    "metered_feature": "codex_auto_review",
                    "rate_limit": {
                        "primary_window": {
                            "used_percent": 17,
                        }
                    },
                },
            ]
        }

        self.assertEqual(usage.sensor_value(payload, usage.CODE_REVIEW_USAGE), 17)
        self.assertEqual(
            usage.sensor_attributes(payload, usage.CODE_REVIEW_USAGE),
            {
                "metered_feature": "codex_auto_review",
                "limit_name": "Core review",
            },
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
        self.assertEqual(
            usage.parse_timestamp(0).isoformat(),
            "1970-01-01T00:00:00+00:00",
        )
        self.assertIsNone(usage.parse_timestamp(""))
        self.assertIsNone(usage.parse_timestamp(None))


if __name__ == "__main__":
    unittest.main()

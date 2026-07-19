"""Tests for current Codex usage fields outside the core fixed windows."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

USAGE_PATH = (
    Path(__file__).parents[1]
    / "custom_components"
    / "hass_codex_usage"
    / "usage.py"
)
SPEC = importlib.util.spec_from_file_location(
    "hass_codex_usage_latest_schema", USAGE_PATH
)
assert SPEC is not None and SPEC.loader is not None
usage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(usage)


class LatestUsageSchemaTest(unittest.TestCase):
    """Test fields verified in the latest official Codex schema."""

    def test_known_nonfixed_windows_are_not_positionally_relabelled(self) -> None:
        """Leave daily, monthly, and annual limits out of fixed sensors."""
        for primary_seconds, secondary_seconds in (
            (24 * 60 * 60, 30 * 24 * 60 * 60),
            (365 * 24 * 60 * 60, 24 * 60 * 60),
        ):
            with self.subTest(
                primary_seconds=primary_seconds,
                secondary_seconds=secondary_seconds,
            ):
                # Given: both windows have known, unsupported durations.
                payload = {
                    "rate_limit": {
                        "primary_window": {
                            "used_percent": 10,
                            "limit_window_seconds": primary_seconds,
                        },
                        "secondary_window": {
                            "used_percent": 20,
                            "limit_window_seconds": secondary_seconds,
                        },
                    }
                }

                # When: fixed session and weekly values are parsed.
                values = (
                    usage.sensor_value(payload, usage.SESSION_USAGE_REMAINING),
                    usage.sensor_value(payload, usage.WEEKLY_USAGE_REMAINING),
                )

                # Then: positional fallback does not invent either fixed limit.
                self.assertEqual(values, (None, None))

    def test_reset_credits_and_reached_reason_are_exposed(self) -> None:
        """Expose the current fixed summary and reached-reason fields."""
        # Given: the current usage summary shape.
        payload = {
            "rate_limit": {
                "primary_window": {
                    "used_percent": 10,
                    "limit_window_seconds": 5 * 60 * 60,
                }
            },
            "rate_limit_reached_type": {
                "type": "workspace_member_credits_depleted"
            },
            "rate_limit_reset_credits": {"available_count": 1},
        }

        # When: the reset-credit state and session attributes are read.
        reset_key = "rate_limit_reset_credits_available"
        reset_value = usage.sensor_value(payload, reset_key)
        reset_attributes = usage.sensor_attributes(payload, reset_key)
        session_attributes = usage.sensor_attributes(
            payload, usage.SESSION_USAGE_REMAINING
        )

        # Then: both current fields are exposed without invented values.
        self.assertIn(reset_key, usage.SENSOR_KEYS)
        self.assertEqual(reset_value, 1)
        self.assertEqual(reset_attributes, {"available_count": 1})
        self.assertEqual(
            session_attributes["rate_limit_reached_type"],
            "workspace_member_credits_depleted",
        )


if __name__ == "__main__":
    unittest.main()

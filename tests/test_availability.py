"""Tests for account-specific sensor availability."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = ROOT / "custom_components" / "hass_codex_usage"
AVAILABILITY_PATH = INTEGRATION_DIR / "availability.py"


def _load_module(module_name: str, path: Path) -> types.ModuleType:
    specification = importlib.util.spec_from_file_location(module_name, path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


def _load_availability_modules() -> tuple[types.ModuleType, types.ModuleType]:
    package_name = "hass_codex_usage_availability_test"
    package = types.ModuleType(package_name)
    package.__path__ = [str(INTEGRATION_DIR)]
    sys.modules[package_name] = package
    usage = _load_module(f"{package_name}.usage", INTEGRATION_DIR / "usage.py")
    availability = _load_module(f"{package_name}.availability", AVAILABILITY_PATH)
    return usage, availability


class SensorAvailabilityTest(unittest.TestCase):
    """Test sensors enabled from fields returned for one account."""

    def test_weekly_only_account_disables_absent_feature_groups(self) -> None:
        """Keep returned summaries and disable absent optional limits."""
        # Given: the backend shape corresponding to the user's current screens.
        self.assertTrue(AVAILABILITY_PATH.is_file(), "availability module missing")
        usage, availability = _load_availability_modules()
        payload = {
            "plan_type": "pro",
            "rate_limit": {
                "primary_window": {
                    "used_percent": 30,
                    "limit_window_seconds": 7 * 24 * 60 * 60,
                    "reset_at": 1784937600,
                }
            },
            "credits": {"balance": 0.0},
            "rate_limit_reset_credits": {"available_count": 3},
        }

        # When: account-supported sensor keys are selected.
        supported = availability.supported_sensor_keys(payload)

        # Then: only backend-provided feature groups remain enabled.
        self.assertEqual(
            supported,
            {
                usage.WEEKLY_USAGE_REMAINING,
                usage.WEEKLY_RESET_TIME,
                usage.PLAN,
                usage.EXTRA_USAGE_BALANCE,
                usage.RATE_LIMIT_RESET_CREDITS_AVAILABLE,
            },
        )

    def test_current_schema_payload_enables_every_parsed_feature_group(self) -> None:
        """Keep supported optional features visible when the backend returns them."""
        # Given: current official-schema objects for every fixed sensor group.
        self.assertTrue(AVAILABILITY_PATH.is_file(), "availability module missing")
        usage, availability = _load_availability_modules()
        window = {
            "used_percent": 10,
            "limit_window_seconds": 5 * 60 * 60,
            "reset_at": 1784937600,
        }
        payload = {
            "plan_type": "pro",
            "rate_limit": {
                "primary_window": window,
                "secondary_window": {
                    **window,
                    "limit_window_seconds": 7 * 24 * 60 * 60,
                },
            },
            "additional_rate_limits": [
                {
                    "metered_feature": "codex_auto_review",
                    "rate_limit": {"primary_window": window},
                }
            ],
            "spend_control": {
                "individual_limit": {
                    "remaining_percent": 90,
                    "used": "1",
                    "limit": "10",
                    "reset_at": 1784937600,
                }
            },
            "credits": {"balance": "4"},
            "rate_limit_reset_credits": {"available_count": 1},
        }

        # When: account-supported sensor keys are selected.
        supported = availability.supported_sensor_keys(payload)

        # Then: no supported field is lost by the integration.
        self.assertEqual(supported, set(usage.SENSOR_KEYS))

    def test_registry_state_changes_only_integration_managed_entities(self) -> None:
        """Disable unsupported entities without overriding user choices."""
        # Given: existing enabled, integration-disabled, and user-disabled entries.
        self.assertTrue(AVAILABILITY_PATH.is_file(), "availability module missing")
        _, availability = _load_availability_modules()

        # When: support is removed or later restored.
        states = (
            availability.registry_disabled_by(False, None, "integration"),
            availability.registry_disabled_by(True, "integration", "integration"),
            availability.registry_disabled_by(False, "user", "integration"),
            availability.registry_disabled_by(True, "user", "integration"),
        )

        # Then: only the integration's own disabled state changes.
        self.assertEqual(states, ("integration", None, "user", "user"))


if __name__ == "__main__":
    unittest.main()

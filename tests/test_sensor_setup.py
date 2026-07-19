"""Tests for account-specific Home Assistant sensor setup."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import importlib.util
from pathlib import Path
import sys
import types
from typing import Any
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = ROOT / "custom_components" / "hass_codex_usage"


@dataclass(frozen=True, slots=True, kw_only=True)
class StubSensorEntityDescription:
    """Minimal dataclass-compatible sensor description."""

    key: str
    translation_key: str | None = None
    native_unit_of_measurement: str | None = None
    state_class: str | None = None
    device_class: str | None = None


class StubCoordinatorEntity:
    """Minimal coordinator entity base."""

    @classmethod
    def __class_getitem__(cls, item: Any) -> type[StubCoordinatorEntity]:
        """Support the runtime generic subscription."""
        return cls

    def __init__(self, coordinator: Any) -> None:
        """Store the coordinator like Home Assistant does."""
        self.coordinator = coordinator


class StubRegistryEntryDisabler(StrEnum):
    """Current Home Assistant registry disabler values."""

    CONFIG_ENTRY = "config_entry"
    DEVICE = "device"
    HASS = "hass"
    INTEGRATION = "integration"
    USER = "user"


def _load_module(module_name: str, path: Path) -> types.ModuleType:
    specification = importlib.util.spec_from_file_location(module_name, path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


def _load_sensor_module() -> types.ModuleType:
    package_name = "hass_codex_usage_sensor_test"
    package = types.ModuleType(package_name)
    package.__path__ = [str(INTEGRATION_DIR)]

    sensor_component = types.ModuleType("homeassistant.components.sensor")
    sensor_component.SensorDeviceClass = types.SimpleNamespace(TIMESTAMP="timestamp")
    sensor_component.SensorEntity = type("SensorEntity", (), {})
    sensor_component.SensorEntityDescription = StubSensorEntityDescription
    sensor_component.SensorStateClass = types.SimpleNamespace(MEASUREMENT="measurement")
    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = type("ConfigEntry", (), {})
    ha_const = types.ModuleType("homeassistant.const")
    ha_const.PERCENTAGE = "%"
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = type("HomeAssistant", (), {})
    helpers = types.ModuleType("homeassistant.helpers")
    device_registry = types.ModuleType("homeassistant.helpers.device_registry")
    device_registry.DeviceEntryType = types.SimpleNamespace(SERVICE="service")
    entity_platform = types.ModuleType("homeassistant.helpers.entity_platform")
    entity_platform.AddEntitiesCallback = Any
    entity_registry = types.ModuleType("homeassistant.helpers.entity_registry")
    entity_registry.RegistryEntryDisabler = StubRegistryEntryDisabler
    entity_registry.async_get = lambda hass: hass.entity_registry
    update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")
    update_coordinator.CoordinatorEntity = StubCoordinatorEntity
    coordinator = types.ModuleType(f"{package_name}.coordinator")
    coordinator.CodexUsageCoordinator = type("CodexUsageCoordinator", (), {})

    stub_modules = {
        package_name: package,
        "homeassistant": types.ModuleType("homeassistant"),
        "homeassistant.components": types.ModuleType("homeassistant.components"),
        "homeassistant.components.sensor": sensor_component,
        "homeassistant.config_entries": config_entries,
        "homeassistant.const": ha_const,
        "homeassistant.core": core,
        "homeassistant.helpers": helpers,
        "homeassistant.helpers.device_registry": device_registry,
        "homeassistant.helpers.entity_platform": entity_platform,
        "homeassistant.helpers.entity_registry": entity_registry,
        "homeassistant.helpers.update_coordinator": update_coordinator,
        f"{package_name}.coordinator": coordinator,
    }
    with mock.patch.dict(sys.modules, stub_modules):
        _load_module(f"{package_name}.const", INTEGRATION_DIR / "const.py")
        _load_module(f"{package_name}.usage", INTEGRATION_DIR / "usage.py")
        _load_module(
            f"{package_name}.availability", INTEGRATION_DIR / "availability.py"
        )
        return _load_module(f"{package_name}.sensor", INTEGRATION_DIR / "sensor.py")


class FakeEntityRegistry:
    """Small entity registry capturing disabled-state changes."""

    def __init__(self, states: dict[str, StubRegistryEntryDisabler | None]) -> None:
        """Create entries addressed by their unique IDs."""
        self.entries = {
            f"sensor.{unique_id}": types.SimpleNamespace(disabled_by=disabled_by)
            for unique_id, disabled_by in states.items()
        }

    def async_get_entity_id(
        self, domain: str, platform: str, unique_id: str
    ) -> str | None:
        """Resolve one registered entity."""
        entity_id = f"{domain}.{unique_id}"
        return entity_id if entity_id in self.entries else None

    def async_get(self, entity_id: str) -> Any:
        """Return one registered entry."""
        return self.entries.get(entity_id)

    def async_update_entity(
        self,
        entity_id: str,
        *,
        disabled_by: StubRegistryEntryDisabler | None,
    ) -> None:
        """Capture a disabled-state update."""
        self.entries[entity_id].disabled_by = disabled_by


class SensorSetupTest(unittest.IsolatedAsyncioTestCase):
    """Test sensor registry behavior without Home Assistant dependencies."""

    async def test_setup_disables_only_absent_integration_managed_sensors(self) -> None:
        """Hide absent features and preserve user-disabled entries."""
        # Given: a weekly-only response and registry entries from an older release.
        sensor = _load_sensor_module()
        entry = types.SimpleNamespace(entry_id="entry-1", title="Codex")
        coordinator = types.SimpleNamespace(
            data={
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
            },
            last_success_time=None,
        )

        def unique_id(key: str) -> str:
            """Build the integration's entity unique ID."""
            return f"{entry.entry_id}_{key}"

        registry = FakeEntityRegistry(
            {
                unique_id("session_usage_remaining"): None,
                unique_id(
                    "weekly_usage_remaining"
                ): StubRegistryEntryDisabler.INTEGRATION,
                unique_id(
                    "code_review_usage_remaining"
                ): StubRegistryEntryDisabler.USER,
            }
        )
        hass = types.SimpleNamespace(
            data={sensor.DOMAIN: {entry.entry_id: coordinator}},
            entity_registry=registry,
        )
        added: list[Any] = []

        # When: the sensor platform is set up after the first coordinator refresh.
        await sensor.async_setup_entry(
            hass, entry, lambda entities: added.extend(entities)
        )

        # Then: integration-managed states follow support while user state is preserved.
        self.assertEqual(
            registry.entries[
                f"sensor.{unique_id('session_usage_remaining')}"
            ].disabled_by,
            StubRegistryEntryDisabler.INTEGRATION,
        )
        self.assertIsNone(
            registry.entries[
                f"sensor.{unique_id('weekly_usage_remaining')}"
            ].disabled_by
        )
        self.assertEqual(
            registry.entries[
                f"sensor.{unique_id('code_review_usage_remaining')}"
            ].disabled_by,
            StubRegistryEntryDisabler.USER,
        )
        defaults = {
            entity.entity_description.key: entity.entity_registry_enabled_default
            for entity in added
        }
        self.assertFalse(defaults["session_usage_remaining"])
        self.assertTrue(defaults["weekly_usage_remaining"])
        self.assertFalse(defaults["extra_usage_remaining"])
        self.assertTrue(defaults["extra_usage_balance"])


if __name__ == "__main__":
    unittest.main()

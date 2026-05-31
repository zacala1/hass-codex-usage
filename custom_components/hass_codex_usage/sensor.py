"""Sensor platform for Codex Usage."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import CODEX_USAGE_ENDPOINT_LABEL, DOMAIN, VERSION
from .coordinator import CodexUsageCoordinator


@dataclass(frozen=True, kw_only=True)
class CodexUsageSensorDescription(SensorEntityDescription):
    """Description for a Codex usage sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


def _nested_value(data: dict[str, Any], *path: str) -> Any:
    """Return a nested value from a dictionary."""
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _rate_limit_value(data: dict[str, Any], window: str, field: str) -> Any:
    """Read a rate-limit field from the expected Codex usage schema."""
    return _nested_value(data, "rate_limits", window, field)


def _parse_timestamp(value: Any) -> datetime | None:
    """Parse an API timestamp into a Home Assistant datetime value."""
    if not isinstance(value, str):
        return None
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None
    return parsed if parsed.tzinfo else dt_util.as_utc(parsed)


SENSOR_DESCRIPTIONS: tuple[CodexUsageSensorDescription, ...] = (
    CodexUsageSensorDescription(
        key="session_usage",
        translation_key="session_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _rate_limit_value(
            data, "primary_window", "used_percent"
        ),
    ),
    CodexUsageSensorDescription(
        key="session_reset_time",
        translation_key="session_reset_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: _parse_timestamp(
            _rate_limit_value(data, "primary_window", "reset_at")
        ),
    ),
    CodexUsageSensorDescription(
        key="weekly_usage",
        translation_key="weekly_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _rate_limit_value(
            data, "secondary_window", "used_percent"
        ),
    ),
    CodexUsageSensorDescription(
        key="weekly_reset_time",
        translation_key="weekly_reset_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: _parse_timestamp(
            _rate_limit_value(data, "secondary_window", "reset_at")
        ),
    ),
    CodexUsageSensorDescription(
        key="plan",
        translation_key="plan",
        value_fn=lambda data: data.get("plan"),
    ),
    CodexUsageSensorDescription(
        key="code_review_usage",
        translation_key="code_review_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _rate_limit_value(
            data, "code_review_rate_limit", "used_percent"
        ),
    ),
    CodexUsageSensorDescription(
        key="code_review_reset_time",
        translation_key="code_review_reset_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: _parse_timestamp(
            _rate_limit_value(data, "code_review_rate_limit", "reset_at")
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Codex Usage sensors from a config entry."""
    coordinator: CodexUsageCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        CodexUsageSensor(coordinator, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class CodexUsageSensor(CoordinatorEntity[CodexUsageCoordinator], SensorEntity):
    """Representation of a Codex usage sensor."""

    entity_description: CodexUsageSensorDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CodexUsageCoordinator,
        entry: ConfigEntry,
        description: CodexUsageSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "manufacturer": "OpenAI",
            "name": entry.title,
            "entry_type": dr.DeviceEntryType.SERVICE,
        }

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return sensor attributes."""
        data = self.coordinator.data or {}
        last_updated = self.coordinator.last_success_time
        return {
            "account_email": data.get("account_email"),
            "integration_version": VERSION,
            "last_updated": last_updated.isoformat() if last_updated else None,
            "api_endpoint": data.get("_api_endpoint", CODEX_USAGE_ENDPOINT_LABEL),
        }

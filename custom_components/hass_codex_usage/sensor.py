"""Sensor platform for Codex Usage."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
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

from .const import CODEX_USAGE_ENDPOINT_LABEL, DOMAIN, VERSION
from .coordinator import CodexUsageCoordinator
from .usage import (
    CODE_REVIEW_RESET_TIME,
    CODE_REVIEW_USAGE,
    PLAN,
    SESSION_RESET_TIME,
    SESSION_USAGE,
    WEEKLY_RESET_TIME,
    WEEKLY_USAGE,
    sensor_value,
)


@dataclass(frozen=True, kw_only=True)
class CodexUsageSensorDescription(SensorEntityDescription):
    """Description for a Codex usage sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSOR_DESCRIPTIONS: tuple[CodexUsageSensorDescription, ...] = (
    CodexUsageSensorDescription(
        key=SESSION_USAGE,
        translation_key="session_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sensor_value(data, SESSION_USAGE),
    ),
    CodexUsageSensorDescription(
        key=SESSION_RESET_TIME,
        translation_key="session_reset_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: sensor_value(data, SESSION_RESET_TIME),
    ),
    CodexUsageSensorDescription(
        key=WEEKLY_USAGE,
        translation_key="weekly_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sensor_value(data, WEEKLY_USAGE),
    ),
    CodexUsageSensorDescription(
        key=WEEKLY_RESET_TIME,
        translation_key="weekly_reset_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: sensor_value(data, WEEKLY_RESET_TIME),
    ),
    CodexUsageSensorDescription(
        key=PLAN,
        translation_key="plan",
        value_fn=lambda data: sensor_value(data, PLAN),
    ),
    CodexUsageSensorDescription(
        key=CODE_REVIEW_USAGE,
        translation_key="code_review_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sensor_value(data, CODE_REVIEW_USAGE),
    ),
    CodexUsageSensorDescription(
        key=CODE_REVIEW_RESET_TIME,
        translation_key="code_review_reset_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: sensor_value(data, CODE_REVIEW_RESET_TIME),
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
        meta = data.get("_meta", {})
        if not isinstance(meta, dict):
            meta = {}
        last_updated = self.coordinator.last_success_time
        return {
            "account_email": meta.get("account_email"),
            "integration_version": VERSION,
            "last_updated": last_updated.isoformat() if last_updated else None,
            "api_endpoint": meta.get("api_endpoint", CODEX_USAGE_ENDPOINT_LABEL),
        }

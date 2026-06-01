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
from homeassistant.const import PERCENTAGE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CODEX_USAGE_ENDPOINT_LABEL, DOMAIN, VERSION
from .coordinator import CodexUsageCoordinator
from .usage import (
    CODE_REVIEW_RESET_TIME,
    CODE_REVIEW_USAGE,
    CODEX_SPARK_RESET_TIME,
    CODEX_SPARK_USAGE,
    CODEX_SPARK_WEEKLY_RESET_TIME,
    CODEX_SPARK_WEEKLY_USAGE,
    EXTRA_USAGE,
    EXTRA_USAGE_CREDITS,
    EXTRA_USAGE_ENABLED,
    EXTRA_USAGE_LIMIT,
    PLAN,
    SESSION_RESET_TIME,
    SESSION_USAGE,
    WEEKLY_RESET_TIME,
    WEEKLY_USAGE,
    sensor_attributes,
    sensor_supported,
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
    CodexUsageSensorDescription(
        key=EXTRA_USAGE_ENABLED,
        translation_key="extra_usage_enabled",
        value_fn=lambda data: sensor_value(data, EXTRA_USAGE_ENABLED),
    ),
    CodexUsageSensorDescription(
        key=EXTRA_USAGE,
        translation_key="extra_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sensor_value(data, EXTRA_USAGE),
    ),
    CodexUsageSensorDescription(
        key=EXTRA_USAGE_CREDITS,
        translation_key="extra_usage_credits",
        native_unit_of_measurement="credits",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sensor_value(data, EXTRA_USAGE_CREDITS),
    ),
    CodexUsageSensorDescription(
        key=EXTRA_USAGE_LIMIT,
        translation_key="extra_usage_limit",
        native_unit_of_measurement="credits",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sensor_value(data, EXTRA_USAGE_LIMIT),
    ),
    CodexUsageSensorDescription(
        key=CODEX_SPARK_USAGE,
        translation_key="codex_spark_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sensor_value(data, CODEX_SPARK_USAGE),
    ),
    CodexUsageSensorDescription(
        key=CODEX_SPARK_RESET_TIME,
        translation_key="codex_spark_reset_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: sensor_value(data, CODEX_SPARK_RESET_TIME),
    ),
    CodexUsageSensorDescription(
        key=CODEX_SPARK_WEEKLY_USAGE,
        translation_key="codex_spark_weekly_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sensor_value(data, CODEX_SPARK_WEEKLY_USAGE),
    ),
    CodexUsageSensorDescription(
        key=CODEX_SPARK_WEEKLY_RESET_TIME,
        translation_key="codex_spark_weekly_reset_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: sensor_value(data, CODEX_SPARK_WEEKLY_RESET_TIME),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Codex Usage sensors from a config entry."""
    coordinator: CodexUsageCoordinator = hass.data[DOMAIN][entry.entry_id]
    data = coordinator.data or {}
    descriptions = tuple(
        description
        for description in SENSOR_DESCRIPTIONS
        if sensor_supported(data, description.key)
    )
    _remove_unsupported_entities(hass, entry, descriptions)
    async_add_entities(
        CodexUsageSensor(coordinator, entry, description)
        for description in descriptions
    )


def _remove_unsupported_entities(
    hass: HomeAssistant,
    entry: ConfigEntry,
    descriptions: tuple[CodexUsageSensorDescription, ...],
) -> None:
    """Remove optional entities that the current usage response cannot support."""
    supported_keys = {description.key for description in descriptions}
    registry = er.async_get(hass)
    for description in SENSOR_DESCRIPTIONS:
        if description.key in supported_keys:
            continue
        entity_id = registry.async_get_entity_id(
            Platform.SENSOR,
            DOMAIN,
            f"{entry.entry_id}_{description.key}",
        )
        if entity_id is not None:
            registry.async_remove(entity_id)


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
        attributes = {
            "account_email": meta.get("account_email"),
            "account_id": meta.get("account_id"),
            "integration_version": VERSION,
            "last_updated": last_updated.isoformat() if last_updated else None,
            "api_endpoint": meta.get("api_endpoint", CODEX_USAGE_ENDPOINT_LABEL),
        }
        attributes.update(
            sensor_attributes(data, self.entity_description.key)
        )
        return attributes

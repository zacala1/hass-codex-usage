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
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .availability import registry_disabled_by, supported_sensor_keys
from .const import CODEX_USAGE_ENDPOINT_LABEL, DOMAIN, VERSION
from .coordinator import CodexUsageCoordinator
from .usage import (
    CODE_REVIEW_RESET_TIME,
    CODE_REVIEW_USAGE_REMAINING,
    EXTRA_USAGE_BALANCE,
    EXTRA_USAGE_LIMIT,
    EXTRA_USAGE_REMAINING,
    EXTRA_USAGE_RESET_TIME,
    EXTRA_USAGE_USED,
    PLAN,
    RATE_LIMIT_RESET_CREDITS_AVAILABLE,
    SENSOR_KEYS,
    SESSION_RESET_TIME,
    SESSION_USAGE_REMAINING,
    WEEKLY_RESET_TIME,
    WEEKLY_USAGE_REMAINING,
    sensor_attributes,
    sensor_value,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class CodexUsageSensorDescription(SensorEntityDescription):
    """Description for a Codex usage sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


SENSOR_DESCRIPTIONS: tuple[CodexUsageSensorDescription, ...] = (
    CodexUsageSensorDescription(
        key=SESSION_USAGE_REMAINING,
        translation_key="session_usage_remaining",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sensor_value(data, SESSION_USAGE_REMAINING),
    ),
    CodexUsageSensorDescription(
        key=SESSION_RESET_TIME,
        translation_key="session_reset_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: sensor_value(data, SESSION_RESET_TIME),
    ),
    CodexUsageSensorDescription(
        key=WEEKLY_USAGE_REMAINING,
        translation_key="weekly_usage_remaining",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sensor_value(data, WEEKLY_USAGE_REMAINING),
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
        key=CODE_REVIEW_USAGE_REMAINING,
        translation_key="code_review_usage_remaining",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sensor_value(data, CODE_REVIEW_USAGE_REMAINING),
    ),
    CodexUsageSensorDescription(
        key=CODE_REVIEW_RESET_TIME,
        translation_key="code_review_reset_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: sensor_value(data, CODE_REVIEW_RESET_TIME),
    ),
    CodexUsageSensorDescription(
        key=EXTRA_USAGE_REMAINING,
        translation_key="extra_usage_remaining",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sensor_value(data, EXTRA_USAGE_REMAINING),
    ),
    CodexUsageSensorDescription(
        key=EXTRA_USAGE_RESET_TIME,
        translation_key="extra_usage_reset_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data: sensor_value(data, EXTRA_USAGE_RESET_TIME),
    ),
    CodexUsageSensorDescription(
        key=EXTRA_USAGE_BALANCE,
        translation_key="extra_usage_balance",
        native_unit_of_measurement="credits",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sensor_value(data, EXTRA_USAGE_BALANCE),
    ),
    CodexUsageSensorDescription(
        key=EXTRA_USAGE_USED,
        translation_key="extra_usage_used",
        native_unit_of_measurement="credits",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sensor_value(data, EXTRA_USAGE_USED),
    ),
    CodexUsageSensorDescription(
        key=EXTRA_USAGE_LIMIT,
        translation_key="extra_usage_limit",
        native_unit_of_measurement="credits",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sensor_value(data, EXTRA_USAGE_LIMIT),
    ),
    CodexUsageSensorDescription(
        key=RATE_LIMIT_RESET_CREDITS_AVAILABLE,
        translation_key="rate_limit_reset_credits_available",
        native_unit_of_measurement="credits",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: sensor_value(data, RATE_LIMIT_RESET_CREDITS_AVAILABLE),
    ),
)

assert tuple(description.key for description in SENSOR_DESCRIPTIONS) == SENSOR_KEYS
assert (
    tuple(description.translation_key for description in SENSOR_DESCRIPTIONS)
    == SENSOR_KEYS
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Codex Usage sensors from a config entry."""
    coordinator: CodexUsageCoordinator = hass.data[DOMAIN][entry.entry_id]
    supported_keys = supported_sensor_keys(coordinator.data or {})
    registry = er.async_get(hass)
    for description in SENSOR_DESCRIPTIONS:
        unique_id = f"{entry.entry_id}_{description.key}"
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, unique_id)
        if entity_id is None:
            continue
        registry_entry = registry.async_get(entity_id)
        if registry_entry is None:
            continue
        disabled_by = registry_disabled_by(
            description.key in supported_keys,
            registry_entry.disabled_by,
            er.RegistryEntryDisabler.INTEGRATION,
        )
        if disabled_by != registry_entry.disabled_by:
            registry.async_update_entity(entity_id, disabled_by=disabled_by)

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
    def entity_registry_enabled_default(self) -> bool:
        """Enable new entities only when the account returns their feature."""
        return self.entity_description.key in supported_sensor_keys(
            self.coordinator.data or {}
        )

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
        attributes.update(sensor_attributes(data, self.entity_description.key))
        if self.entity_description.key == RATE_LIMIT_RESET_CREDITS_AVAILABLE:
            reset_credit_details = meta.get("rate_limit_reset_credits")
            if isinstance(reset_credit_details, dict):
                attributes.update(reset_credit_details)
        return attributes

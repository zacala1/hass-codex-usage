"""Select sensors supported by one Codex usage response."""

from __future__ import annotations

from typing import Any, Final, TypeVar

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
    sensor_value,
)

_SENSOR_GROUPS: Final[tuple[tuple[str, ...], ...]] = (
    (SESSION_USAGE_REMAINING, SESSION_RESET_TIME),
    (WEEKLY_USAGE_REMAINING, WEEKLY_RESET_TIME),
    (PLAN,),
    (CODE_REVIEW_USAGE_REMAINING, CODE_REVIEW_RESET_TIME),
    (
        EXTRA_USAGE_REMAINING,
        EXTRA_USAGE_RESET_TIME,
        EXTRA_USAGE_USED,
        EXTRA_USAGE_LIMIT,
    ),
    (EXTRA_USAGE_BALANCE,),
    (RATE_LIMIT_RESET_CREDITS_AVAILABLE,),
)

assert {key for group in _SENSOR_GROUPS for key in group} == set(SENSOR_KEYS)

RegistryDisablerT = TypeVar("RegistryDisablerT")


def supported_sensor_keys(data: dict[str, Any]) -> set[str]:
    """Return complete sensor groups represented in the response."""
    supported: set[str] = set()
    for group in _SENSOR_GROUPS:
        if any(sensor_value(data, key) is not None for key in group):
            supported.update(group)
    return supported


def registry_disabled_by(
    supported: bool,
    current: RegistryDisablerT | None,
    integration: RegistryDisablerT,
) -> RegistryDisablerT | None:
    """Return a disabled state without overriding non-integration choices."""
    if current == integration:
        return None if supported else current
    if current is None:
        return None if supported else integration
    return current

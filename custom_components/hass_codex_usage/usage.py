"""Codex usage response parsing helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

SESSION_USAGE = "session_usage"
SESSION_RESET_TIME = "session_reset_time"
WEEKLY_USAGE = "weekly_usage"
WEEKLY_RESET_TIME = "weekly_reset_time"
PLAN = "plan"
CODE_REVIEW_USAGE = "code_review_usage"
CODE_REVIEW_RESET_TIME = "code_review_reset_time"

USAGE_PERCENT_FIELDS = ("used_percent", "usage_percent", "percent_used")
RESET_TIME_FIELDS = ("reset_at", "resets_at", "reset_time")
WINDOW_ATTRIBUTE_FIELDS = (
    "allowed",
    "limit_reached",
    "limit_window_seconds",
    "reset_after_seconds",
)

SENSOR_KEYS = (
    SESSION_USAGE,
    SESSION_RESET_TIME,
    WEEKLY_USAGE,
    WEEKLY_RESET_TIME,
    PLAN,
    CODE_REVIEW_USAGE,
    CODE_REVIEW_RESET_TIME,
)

WINDOW_PATHS = {
    "primary_window": (
        ("rate_limit", "primary_window"),
        ("rate_limits", "primary_window"),
        ("primary_window",),
        ("usage", "primary_window"),
    ),
    "secondary_window": (
        ("rate_limit", "secondary_window"),
        ("rate_limits", "secondary_window"),
        ("secondary_window",),
        ("usage", "secondary_window"),
    ),
    "code_review_rate_limit": (
        ("rate_limits", "code_review_rate_limit"),
        ("rate_limits", "code_review"),
        ("code_review_rate_limit",),
        ("code_review",),
    ),
}
CODE_REVIEW_LABEL_FIELDS = ("metered_feature", "limit_name", "id", "name")
SENSOR_WINDOWS = {
    SESSION_USAGE: "primary_window",
    SESSION_RESET_TIME: "primary_window",
    WEEKLY_USAGE: "secondary_window",
    WEEKLY_RESET_TIME: "secondary_window",
    CODE_REVIEW_USAGE: "code_review_rate_limit",
    CODE_REVIEW_RESET_TIME: "code_review_rate_limit",
}


def sensor_value(data: dict[str, Any], key: str) -> Any:
    """Return a sensor value from a Codex usage response."""
    if key == SESSION_USAGE:
        return usage_percent(data, "primary_window")
    if key == SESSION_RESET_TIME:
        return reset_time(data, "primary_window")
    if key == WEEKLY_USAGE:
        return usage_percent(data, "secondary_window")
    if key == WEEKLY_RESET_TIME:
        return reset_time(data, "secondary_window")
    if key == PLAN:
        return plan(data)
    if key == CODE_REVIEW_USAGE:
        return usage_percent(data, "code_review_rate_limit")
    if key == CODE_REVIEW_RESET_TIME:
        return reset_time(data, "code_review_rate_limit")
    return None


def sensor_attributes(data: dict[str, Any], key: str) -> dict[str, Any]:
    """Return extra attributes for a sensor value."""
    window = SENSOR_WINDOWS.get(key)
    if window is None:
        return {}

    attributes = window_attributes(data, window)
    if key in (CODE_REVIEW_USAGE, CODE_REVIEW_RESET_TIME):
        attributes.update(code_review_label_attributes(data))
    return attributes


def usage_percent(data: dict[str, Any], window: str) -> float | int | None:
    """Return a usage percent value from a usage window."""
    value = _window_field(data, window, USAGE_PERCENT_FIELDS)
    return value if type(value) in (int, float) else None


def reset_time(data: dict[str, Any], window: str) -> datetime | None:
    """Return a reset timestamp from a usage window."""
    return parse_timestamp(_window_field(data, window, RESET_TIME_FIELDS))


def window_attributes(data: dict[str, Any], window: str) -> dict[str, Any]:
    """Return known rate-limit metadata for a usage window."""
    window_data = _window_data(data, window)
    if window_data is None:
        return {}

    attributes: dict[str, Any] = {}
    for field in WINDOW_ATTRIBUTE_FIELDS:
        value = window_data.get(field)
        if type(value) in (bool, int, float, str):
            attributes[field] = value
    return attributes


def code_review_label_attributes(data: dict[str, Any]) -> dict[str, str]:
    """Return label attributes for the matched code-review limit."""
    limit = _code_review_limit(data)
    if limit is None:
        return {}

    attributes: dict[str, str] = {}
    for field in CODE_REVIEW_LABEL_FIELDS:
        value = limit.get(field)
        if isinstance(value, str) and value:
            attributes[field] = value
    return attributes


def plan(data: dict[str, Any]) -> str | None:
    """Return the ChatGPT plan from known response locations."""
    value = first_present(
        data,
        ("plan_type",),
        ("plan",),
        ("chatgpt_plan_type",),
        ("account", "plan"),
        ("account", "plan_type"),
    )
    return value if isinstance(value, str) and value else None


def parse_timestamp(value: Any) -> datetime | None:
    """Parse an API timestamp into a timezone-aware datetime."""
    if type(value) in (int, float):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None

    if not isinstance(value, str) or not value:
        return None

    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = f"{candidate[:-1]}+00:00"

    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def first_present(data: dict[str, Any], *paths: tuple[str, ...]) -> Any:
    """Return the first non-None value from the given paths."""
    for path in paths:
        value = nested_value(data, *path)
        if value is not None:
            return value
    return None


def nested_value(data: dict[str, Any], *path: str) -> Any:
    """Return a nested value from a dictionary."""
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _window_field(
    data: dict[str, Any],
    window: str,
    fields: tuple[str, ...],
) -> Any:
    """Return the first matching field from a known usage window location."""
    window_data = _window_data(data, window)
    if window_data is None:
        return None

    for field in fields:
        value = window_data.get(field)
        if value is not None:
            return value

    return None


def _window_data(data: dict[str, Any], window: str) -> dict[str, Any] | None:
    """Return known usage window data."""
    for path in WINDOW_PATHS.get(window, ()):
        window_data = nested_value(data, *path)
        if not isinstance(window_data, dict):
            continue
        return window_data

    if window == "code_review_rate_limit":
        limit = _code_review_limit(data)
        if limit is None:
            return None
        rate_limit = limit.get("rate_limit")
        if isinstance(rate_limit, dict):
            for candidate in (
                rate_limit.get("primary_window"),
                rate_limit.get("secondary_window"),
                rate_limit,
            ):
                if isinstance(candidate, dict):
                    return candidate
        return limit

    return None


def _code_review_field(data: dict[str, Any], fields: tuple[str, ...]) -> Any:
    """Return a code-review limit field from direct or additional limits."""
    limit = _code_review_limit(data)
    if limit is None:
        return None

    value = _field_from_limit(limit.get("rate_limit"), fields)
    if value is not None:
        return value
    return _field_from_limit(limit, fields)


def _code_review_limit(data: dict[str, Any]) -> dict[str, Any] | None:
    """Return a direct or additional code-review limit object."""
    direct_candidates = (
        nested_value(data, "rate_limits", "code_review_rate_limit"),
        nested_value(data, "code_review_rate_limit"),
        nested_value(data, "rate_limits", "code_review"),
        nested_value(data, "code_review"),
    )
    for candidate in direct_candidates:
        if isinstance(candidate, dict):
            return candidate

    additional_limits = first_present(
        data,
        ("additional_rate_limits",),
        ("rate_limits", "additional_rate_limits"),
    )
    if not isinstance(additional_limits, list):
        return None

    for item in additional_limits:
        if isinstance(item, dict) and _is_code_review_limit(item):
            return item

    return None


def _field_from_limit(limit_data: Any, fields: tuple[str, ...]) -> Any:
    """Return a field from a limit object or one of its windows."""
    if not isinstance(limit_data, dict):
        return None

    candidates = (
        limit_data,
        limit_data.get("primary_window"),
        limit_data.get("secondary_window"),
    )
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        for field in fields:
            value = candidate.get(field)
            if value is not None:
                return value

    return None


def _is_code_review_limit(item: dict[str, Any]) -> bool:
    """Return whether an additional limit entry appears to be for code review."""
    for field in CODE_REVIEW_LABEL_FIELDS:
        value = item.get(field)
        if not isinstance(value, str):
            continue
        normalized = value.lower().replace("-", "_").replace(" ", "_")
        if "code_review" in normalized:
            return True
    return False

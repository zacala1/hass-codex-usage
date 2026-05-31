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
        ("rate_limits", "primary_window"),
        ("primary_window",),
        ("usage", "primary_window"),
    ),
    "secondary_window": (
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


def usage_percent(data: dict[str, Any], window: str) -> float | int | None:
    """Return a usage percent value from a usage window."""
    value = _window_field(data, window, USAGE_PERCENT_FIELDS)
    return value if type(value) in (int, float) else None


def reset_time(data: dict[str, Any], window: str) -> datetime | None:
    """Return a reset timestamp from a usage window."""
    return parse_timestamp(_window_field(data, window, RESET_TIME_FIELDS))


def plan(data: dict[str, Any]) -> str | None:
    """Return the ChatGPT plan from known response locations."""
    value = first_present(
        data,
        ("plan",),
        ("chatgpt_plan_type",),
        ("account", "plan"),
        ("account", "plan_type"),
    )
    return value if isinstance(value, str) and value else None


def parse_timestamp(value: Any) -> datetime | None:
    """Parse an API timestamp into a timezone-aware datetime."""
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
    for path in WINDOW_PATHS.get(window, ()):
        window_data = nested_value(data, *path)
        if not isinstance(window_data, dict):
            continue
        for field in fields:
            value = window_data.get(field)
            if value is not None:
                return value
    return None

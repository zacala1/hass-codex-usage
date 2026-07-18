"""Parse the current Codex usage response schema."""

from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any, Final

FIVE_HOUR_WINDOW_SECONDS: Final = 5 * 60 * 60
WEEKLY_WINDOW_SECONDS: Final = 7 * 24 * 60 * 60
WINDOW_DURATION_TOLERANCE: Final = 0.05

SESSION_USAGE_REMAINING = "session_usage_remaining"
SESSION_RESET_TIME = "session_reset_time"
WEEKLY_USAGE_REMAINING = "weekly_usage_remaining"
WEEKLY_RESET_TIME = "weekly_reset_time"
PLAN = "plan"
CODE_REVIEW_USAGE_REMAINING = "code_review_usage_remaining"
CODE_REVIEW_RESET_TIME = "code_review_reset_time"
EXTRA_USAGE_REMAINING = "extra_usage_remaining"
EXTRA_USAGE_RESET_TIME = "extra_usage_reset_time"
EXTRA_USAGE_BALANCE = "extra_usage_balance"
EXTRA_USAGE_USED = "extra_usage_used"
EXTRA_USAGE_LIMIT = "extra_usage_limit"
SENSOR_KEYS = (
    SESSION_USAGE_REMAINING,
    SESSION_RESET_TIME,
    WEEKLY_USAGE_REMAINING,
    WEEKLY_RESET_TIME,
    PLAN,
    CODE_REVIEW_USAGE_REMAINING,
    CODE_REVIEW_RESET_TIME,
    EXTRA_USAGE_REMAINING,
    EXTRA_USAGE_RESET_TIME,
    EXTRA_USAGE_BALANCE,
    EXTRA_USAGE_USED,
    EXTRA_USAGE_LIMIT,
)


def sensor_value(data: dict[str, Any], key: str) -> Any:
    """Return a sensor value from a current Codex usage response."""
    rate_limit = _mapping(data.get("rate_limit"))
    session_window, weekly_window = _subscription_windows(rate_limit)
    if key == SESSION_USAGE_REMAINING:
        return _window_remaining_value(session_window)
    if key == SESSION_RESET_TIME:
        return _window_reset_value(session_window)
    if key == WEEKLY_USAGE_REMAINING:
        return _window_remaining_value(weekly_window)
    if key == WEEKLY_RESET_TIME:
        return _window_reset_value(weekly_window)
    if key == PLAN:
        value = data.get("plan_type")
        return value if isinstance(value, str) and value else None

    code_review = _code_review_rate_limit(data)
    if key == CODE_REVIEW_USAGE_REMAINING:
        return _window_remaining(code_review, "primary_window")
    if key == CODE_REVIEW_RESET_TIME:
        return _window_reset(code_review, "primary_window")

    individual = _individual_limit(data)
    if key == EXTRA_USAGE_REMAINING:
        return _remaining_percent(individual.get("remaining_percent"))
    if key == EXTRA_USAGE_RESET_TIME:
        return parse_timestamp(individual.get("reset_at"))
    if key == EXTRA_USAGE_USED:
        return _credit_number(individual.get("used"))
    if key == EXTRA_USAGE_LIMIT:
        return _credit_number(individual.get("limit"))
    if key == EXTRA_USAGE_BALANCE:
        return _credit_number(_mapping(data.get("credits")).get("balance"))
    return None


def sensor_attributes(data: dict[str, Any], key: str) -> dict[str, Any]:
    """Return allowlisted metadata for a sensor."""
    rate_limit = _mapping(data.get("rate_limit"))
    session_window, weekly_window = _subscription_windows(rate_limit)
    if key in (SESSION_USAGE_REMAINING, SESSION_RESET_TIME):
        return _window_attributes_for_value(rate_limit, session_window)
    if key in (WEEKLY_USAGE_REMAINING, WEEKLY_RESET_TIME):
        return _window_attributes_for_value(rate_limit, weekly_window)

    code_review = _code_review_entry(data)
    if key in (CODE_REVIEW_USAGE_REMAINING, CODE_REVIEW_RESET_TIME):
        attributes = _window_attributes(
            _mapping(code_review.get("rate_limit")), "primary_window"
        )
        _copy_scalars(code_review, attributes, ("metered_feature", "limit_name"))
        return attributes

    if key in (
        EXTRA_USAGE_REMAINING,
        EXTRA_USAGE_RESET_TIME,
        EXTRA_USAGE_USED,
        EXTRA_USAGE_LIMIT,
    ):
        individual = _individual_limit(data)
        attributes: dict[str, Any] = {}
        _copy_scalars(
            individual,
            attributes,
            (
                "source",
                "limit",
                "used",
                "remaining",
                "used_percent",
                "remaining_percent",
                "reset_after_seconds",
                "reset_at",
            ),
        )
        reached = _mapping(data.get("spend_control")).get("reached")
        if isinstance(reached, bool):
            attributes["reached"] = reached
        return attributes

    if key == EXTRA_USAGE_BALANCE:
        credits = _mapping(data.get("credits"))
        attributes = {}
        _copy_scalars(credits, attributes, ("has_credits", "unlimited", "balance"))
        return attributes
    return {}


def parse_timestamp(value: Any) -> datetime | None:
    """Parse the current schema's Unix timestamp."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = _number(value)
        if number is None:
            return None
        try:
            return datetime.fromtimestamp(number, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    return None


def _window_remaining(rate_limit: dict[str, Any], name: str) -> float | int | None:
    return _window_remaining_value(_mapping(rate_limit.get(name)))


def _window_remaining_value(window: dict[str, Any]) -> float | int | None:
    """Return remaining percentage from one selected window."""
    used = _number(window.get("used_percent"))
    if used is None:
        return None
    return _clamp_percent(100 - used)


def _window_reset(rate_limit: dict[str, Any], name: str) -> datetime | None:
    return _window_reset_value(_mapping(rate_limit.get(name)))


def _window_reset_value(window: dict[str, Any]) -> datetime | None:
    """Return reset time from one selected window."""
    return parse_timestamp(window.get("reset_at"))


def _remaining_percent(value: Any) -> float | int | None:
    number = _number(value)
    return _clamp_percent(number) if number is not None else None


def _clamp_percent(value: float | int) -> float | int:
    return max(0, min(100, value))


def _number(value: Any) -> float | int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value if math.isfinite(value) else None
    return None


def _credit_number(value: Any) -> float | int | None:
    number = _number(value)
    if number is not None:
        return number
    if isinstance(value, str) and value.strip():
        try:
            number = float(value)
        except ValueError:
            return None
        return number if math.isfinite(number) else None
    return None


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _subscription_windows(
    rate_limit: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Select session and weekly windows by duration before position."""
    primary = _mapping(rate_limit.get("primary_window"))
    secondary = _mapping(rate_limit.get("secondary_window"))
    windows = (primary, secondary)
    session = _window_by_duration(windows, FIVE_HOUR_WINDOW_SECONDS)
    weekly = _window_by_duration(windows, WEEKLY_WINDOW_SECONDS)

    if not session:
        if primary and not _matches_window_duration(
            primary, WEEKLY_WINDOW_SECONDS
        ):
            session = primary
        elif (
            _matches_window_duration(primary, WEEKLY_WINDOW_SECONDS)
            and secondary
            and not _matches_window_duration(secondary, WEEKLY_WINDOW_SECONDS)
        ):
            session = secondary

    if not weekly and secondary and secondary is not session:
        weekly = secondary
    return session, weekly


def _window_by_duration(
    windows: tuple[dict[str, Any], dict[str, Any]], expected_seconds: int
) -> dict[str, Any]:
    """Return the first window whose duration matches the expected period."""
    for window in windows:
        if _matches_window_duration(window, expected_seconds):
            return window
    return {}


def _matches_window_duration(window: dict[str, Any], expected_seconds: int) -> bool:
    """Match a backend window using Codex's five-percent tolerance."""
    duration = _number(window.get("limit_window_seconds"))
    if duration is None:
        return False
    lower = expected_seconds * (1 - WINDOW_DURATION_TOLERANCE)
    upper = expected_seconds * (1 + WINDOW_DURATION_TOLERANCE)
    return lower <= duration <= upper


def _code_review_entry(data: dict[str, Any]) -> dict[str, Any]:
    entries = data.get("additional_rate_limits")
    if not isinstance(entries, list):
        return {}
    for entry in entries:
        candidate = _mapping(entry)
        if candidate.get("metered_feature") == "codex_auto_review":
            return candidate
    return {}


def _code_review_rate_limit(data: dict[str, Any]) -> dict[str, Any]:
    return _mapping(_code_review_entry(data).get("rate_limit"))


def _individual_limit(data: dict[str, Any]) -> dict[str, Any]:
    spend_control = _mapping(data.get("spend_control"))
    return _mapping(spend_control.get("individual_limit"))


def _window_attributes(
    rate_limit: dict[str, Any], name: str
) -> dict[str, Any]:
    return _window_attributes_for_value(
        rate_limit, _mapping(rate_limit.get(name))
    )


def _window_attributes_for_value(
    rate_limit: dict[str, Any], window: dict[str, Any]
) -> dict[str, Any]:
    """Return allowlisted attributes for one selected window."""
    attributes: dict[str, Any] = {}
    _copy_scalars(rate_limit, attributes, ("allowed", "limit_reached"))
    _copy_scalars(
        window,
        attributes,
        ("limit_window_seconds", "reset_after_seconds"),
    )
    return attributes


def _copy_scalars(
    source: dict[str, Any], target: dict[str, Any], fields: tuple[str, ...]
) -> None:
    for field in fields:
        value = source.get(field)
        if isinstance(value, (str, int, float, bool)) and (
            not isinstance(value, float) or math.isfinite(value)
        ):
            target[field] = value

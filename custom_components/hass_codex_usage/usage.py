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
EXTRA_USAGE_ENABLED = "extra_usage_enabled"
EXTRA_USAGE = "extra_usage"
EXTRA_USAGE_CREDITS = "extra_usage_credits"
EXTRA_USAGE_LIMIT = "extra_usage_limit"
CODEX_SPARK_USAGE = "codex_spark_usage"
CODEX_SPARK_RESET_TIME = "codex_spark_reset_time"
CODEX_SPARK_WEEKLY_USAGE = "codex_spark_weekly_usage"
CODEX_SPARK_WEEKLY_RESET_TIME = "codex_spark_weekly_reset_time"

USAGE_PERCENT_FIELDS = ("used_percent", "usage_percent", "percent_used", "utilization")
RESET_TIME_FIELDS = ("reset_at", "resets_at", "reset_time")
WINDOW_ATTRIBUTE_FIELDS = (
    "allowed",
    "limit_reached",
    "limit_window_seconds",
    "reset_after_seconds",
)
EXTRA_USAGE_ENABLED_FIELDS = (
    "has_credits",
    "unlimited",
    "is_enabled",
    "enabled",
    "extra_usage_enabled",
    "flexible_usage_enabled",
    "credits_enabled",
)
EXTRA_USAGE_EXHAUSTED_FIELDS = (
    "overage_limit_reached",
    "reached",
    "out_of_credits",
)
EXTRA_USAGE_USED_FIELDS = (
    "used_credits",
    "credits_used",
    "usage_credits",
    "credit_usage",
    "used",
    "used_amount",
    "usage_amount",
    "current_usage",
    "total_usage",
    "spent",
    "spend",
)
EXTRA_USAGE_BALANCE_FIELDS = (
    "balance",
    "credit_balance",
    "available_credits",
    "remaining_credits",
    "credits_remaining",
    "remaining",
    "available",
    "remaining_balance",
    "available_balance",
    "current_balance",
)
EXTRA_USAGE_CREDIT_FIELDS = EXTRA_USAGE_USED_FIELDS + EXTRA_USAGE_BALANCE_FIELDS
EXTRA_USAGE_LIMIT_FIELDS = (
    "monthly_limit",
    "credit_limit",
    "spend_limit",
    "limit",
    "max_credits",
    "total_credits",
    "quota",
    "budget",
    "monthly_budget",
    "spending_limit",
    "hard_limit",
    "hard_limit_usd",
    "soft_limit",
    "soft_limit_usd",
    "max_amount",
    "amount_limit",
    "usage_limit",
    "credit_quota",
)
EXTRA_USAGE_ATTRIBUTE_FIELDS = (
    "auto_top_up_enabled",
    "currency",
    "has_credits",
    "unlimited",
    "overage_limit_reached",
    "reached",
    "out_of_credits",
    "balance",
    "credit_balance",
    "available_credits",
    "remaining_credits",
    "credits_remaining",
    "used_credits",
    "credits_used",
    "monthly_limit",
    "credit_limit",
    "spend_limit",
    "limit",
)

SENSOR_KEYS = (
    SESSION_USAGE,
    SESSION_RESET_TIME,
    WEEKLY_USAGE,
    WEEKLY_RESET_TIME,
    PLAN,
    CODE_REVIEW_USAGE,
    CODE_REVIEW_RESET_TIME,
    EXTRA_USAGE_ENABLED,
    EXTRA_USAGE,
    EXTRA_USAGE_CREDITS,
    EXTRA_USAGE_LIMIT,
    CODEX_SPARK_USAGE,
    CODEX_SPARK_RESET_TIME,
    CODEX_SPARK_WEEKLY_USAGE,
    CODEX_SPARK_WEEKLY_RESET_TIME,
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
EXTRA_USAGE_LABEL_FIELDS = ("metered_feature", "limit_name", "id", "name")
SPARK_LABEL_FIELDS = ("metered_feature", "limit_name", "id", "name")
SENSOR_WINDOWS = {
    SESSION_USAGE: "primary_window",
    SESSION_RESET_TIME: "primary_window",
    WEEKLY_USAGE: "secondary_window",
    WEEKLY_RESET_TIME: "secondary_window",
    CODE_REVIEW_USAGE: "code_review_rate_limit",
    CODE_REVIEW_RESET_TIME: "code_review_rate_limit",
    CODEX_SPARK_USAGE: "codex_spark",
    CODEX_SPARK_RESET_TIME: "codex_spark",
    CODEX_SPARK_WEEKLY_USAGE: "codex_spark_weekly",
    CODEX_SPARK_WEEKLY_RESET_TIME: "codex_spark_weekly",
}
ALWAYS_SUPPORTED_SENSOR_KEYS = (
    SESSION_USAGE,
    SESSION_RESET_TIME,
    WEEKLY_USAGE,
    WEEKLY_RESET_TIME,
    PLAN,
)


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
    if key == EXTRA_USAGE_ENABLED:
        return extra_usage_enabled(data)
    if key == EXTRA_USAGE:
        return extra_usage_percent(data)
    if key == EXTRA_USAGE_CREDITS:
        return extra_usage_credits(data)
    if key == EXTRA_USAGE_LIMIT:
        return extra_usage_limit(data)
    if key == CODEX_SPARK_USAGE:
        return usage_percent(data, "codex_spark")
    if key == CODEX_SPARK_RESET_TIME:
        return reset_time(data, "codex_spark")
    if key == CODEX_SPARK_WEEKLY_USAGE:
        return usage_percent(data, "codex_spark_weekly")
    if key == CODEX_SPARK_WEEKLY_RESET_TIME:
        return reset_time(data, "codex_spark_weekly")
    return None


def sensor_attributes(data: dict[str, Any], key: str) -> dict[str, Any]:
    """Return extra attributes for a sensor value."""
    if key in (
        EXTRA_USAGE_ENABLED,
        EXTRA_USAGE,
        EXTRA_USAGE_CREDITS,
        EXTRA_USAGE_LIMIT,
    ):
        return extra_usage_attributes(data)

    window = SENSOR_WINDOWS.get(key)
    if window is None:
        return {}
    attributes = window_attributes(data, window)
    if key in (CODE_REVIEW_USAGE, CODE_REVIEW_RESET_TIME):
        attributes.update(code_review_label_attributes(data))
    if key in (
        CODEX_SPARK_USAGE,
        CODEX_SPARK_RESET_TIME,
        CODEX_SPARK_WEEKLY_USAGE,
        CODEX_SPARK_WEEKLY_RESET_TIME,
    ):
        attributes.update(spark_label_attributes(data))
    return attributes


def sensor_supported(data: dict[str, Any], key: str) -> bool:
    """Return whether a sensor is supported by the current usage response."""
    if key in ALWAYS_SUPPORTED_SENSOR_KEYS:
        return True
    return sensor_value(data, key) is not None


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


def spark_label_attributes(data: dict[str, Any]) -> dict[str, Any]:
    """Return label attributes for the matched Codex Spark limit."""
    limit = _spark_limit(data)
    if limit is None:
        return {}

    attributes: dict[str, Any] = {}
    rate_limit = limit.get("rate_limit")
    if isinstance(rate_limit, dict):
        for field in ("allowed", "limit_reached"):
            value = rate_limit.get(field)
            if type(value) in (bool, int, float, str):
                attributes[field] = value

    for field in SPARK_LABEL_FIELDS:
        value = limit.get(field)
        if isinstance(value, str) and value:
            attributes[field] = value
    return attributes


def extra_usage_enabled(data: dict[str, Any]) -> bool | None:
    """Return whether paid flexible/extra usage appears enabled."""
    return _extra_usage_state(data)


def _extra_usage_state(data: dict[str, Any]) -> bool | None:
    """Return the known enabled state of paid flexible/extra usage."""
    saw_disabled_source = False
    for source in _extra_usage_sources(data):
        value = _first_bool_field(source, EXTRA_USAGE_ENABLED_FIELDS)
        if value is True:
            return True
        if value is False:
            saw_disabled_source = True

        if _first_bool_field(source, EXTRA_USAGE_EXHAUSTED_FIELDS) is True:
            return True

    credits = extra_usage_credits(data)
    if saw_disabled_source and not _is_positive_number(credits):
        return False
    if credits is not None or _extra_usage_numeric(data, EXTRA_USAGE_LIMIT_FIELDS) is not None:
        return True
    return None


def extra_usage_percent(data: dict[str, Any]) -> float | int | None:
    """Return paid flexible/extra usage percent when available."""
    if _extra_usage_state(data) is False:
        return 0

    for source in _extra_usage_sources(data):
        value = _first_numeric_field(source, USAGE_PERCENT_FIELDS)
        if value is not None:
            return value

    limit = extra_usage_limit(data)
    if limit in (None, 0):
        return None

    used = _extra_usage_numeric(data, EXTRA_USAGE_USED_FIELDS)
    if used is not None:
        return _clamped_percent((used / limit) * 100)

    remaining = _extra_usage_numeric(data, EXTRA_USAGE_BALANCE_FIELDS)
    if remaining is not None:
        return _clamped_percent(((limit - remaining) / limit) * 100)

    return None


def extra_usage_credits(data: dict[str, Any]) -> float | int | None:
    """Return paid flexible/extra usage credits when available."""
    used = _extra_usage_numeric(data, EXTRA_USAGE_USED_FIELDS)
    if used is not None:
        return used
    return _extra_usage_numeric(data, EXTRA_USAGE_BALANCE_FIELDS)


def extra_usage_limit(data: dict[str, Any]) -> float | int | None:
    """Return paid flexible/extra usage credit limit when available."""
    limit = _extra_usage_numeric(data, EXTRA_USAGE_LIMIT_FIELDS)
    if limit is not None:
        return limit
    if _extra_usage_state(data) is False:
        return 0
    return None


def extra_usage_attributes(data: dict[str, Any]) -> dict[str, Any]:
    """Return attributes for flexible/extra usage sensors."""
    attributes: dict[str, Any] = {}
    limit = _extra_usage_limit(data)
    if limit is not None:
        for field in EXTRA_USAGE_LABEL_FIELDS:
            value = limit.get(field)
            if isinstance(value, str) and value:
                attributes[field] = value

    for source in _extra_usage_sources(data):
        for field in EXTRA_USAGE_ATTRIBUTE_FIELDS:
            if field in attributes:
                continue
            value = source.get(field)
            if type(value) in (bool, int, float, str):
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


def _clamped_percent(value: float | int) -> float:
    """Return a percentage clamped to the Home Assistant-friendly 0-100 range."""
    return round(max(0, min(100, value)), 1)


def _is_positive_number(value: Any) -> bool:
    """Return whether a value is a positive JSON number."""
    return type(value) in (int, float) and value > 0


def _extra_usage_numeric(
    data: dict[str, Any],
    fields: tuple[str, ...],
) -> float | int | None:
    """Return a numeric extra-usage field from known response locations."""
    sources = _extra_usage_sources(data)
    return _first_numeric_from_sources(sources, fields)


def _first_numeric_from_sources(
    sources: tuple[dict[str, Any], ...],
    fields: tuple[str, ...],
) -> float | int | None:
    """Return the first numeric field from a list of source objects."""
    for source in sources:
        value = _first_numeric_field(source, fields)
        if value is not None:
            return value
    return None


def _first_numeric_field(
    source: dict[str, Any],
    fields: tuple[str, ...],
) -> float | int | None:
    """Return the first valid numeric field from a source object."""
    for field in fields:
        value = _numeric_value(source.get(field))
        if value is not None:
            return value
    return None


def _numeric_value(value: Any) -> float | int | None:
    """Return a numeric value from a JSON number or numeric string."""
    if type(value) in (int, float):
        return value
    if not isinstance(value, str):
        return None

    candidate = value.strip()
    if not candidate:
        return None
    candidate = candidate.replace(",", "")
    if candidate[0] == "$":
        candidate = candidate[1:].strip()

    try:
        parsed = float(candidate)
    except ValueError:
        return None
    if parsed.is_integer():
        return int(parsed)
    return parsed


def _first_bool_field(
    source: dict[str, Any],
    fields: tuple[str, ...],
) -> bool | None:
    """Return the first valid boolean field from a source object."""
    for field in fields:
        value = source.get(field)
        if type(value) is bool:
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in ("true", "yes", "1"):
                return True
            if normalized in ("false", "no", "0"):
                return False
    return None


def _extra_usage_sources(data: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    """Return possible flexible/extra usage source objects."""
    sources: list[dict[str, Any]] = []
    for path in (
        ("extra_usage",),
        ("flexible_usage",),
        ("credits",),
        ("spend_control",),
        ("billing",),
        ("billing", "credits"),
        ("billing", "spend_control"),
        ("account", "credits"),
        ("account", "spend_control"),
        ("subscription", "credits"),
        ("subscription", "spend_control"),
        ("codex", "credits"),
        ("codex", "spend_control"),
        ("usage", "extra_usage"),
        ("usage", "credits"),
        ("usage", "spend_control"),
        ("rate_limit_reset_credits",),
        ("credit_grants",),
        ("credit_summary",),
        ("usage_credits",),
    ):
        source = nested_value(data, *path)
        if isinstance(source, dict):
            sources.append(source)

    limit = _extra_usage_limit(data)
    if limit is not None:
        sources.append(limit)
        for field in ("credits", "spend_control", "rate_limit_reset_credits"):
            value = limit.get(field)
            if isinstance(value, dict):
                sources.append(value)
        rate_limit = limit.get("rate_limit")
        if isinstance(rate_limit, dict):
            sources.append(rate_limit)
            for field in ("primary_window", "secondary_window"):
                value = rate_limit.get(field)
                if isinstance(value, dict):
                    sources.append(value)

    return tuple(sources)


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

    if window in ("codex_spark", "codex_spark_weekly"):
        limit = _spark_limit(data)
        if limit is None:
            return None

        field = "primary_window" if window == "codex_spark" else "secondary_window"
        rate_limit = limit.get("rate_limit")
        if isinstance(rate_limit, dict):
            candidate = rate_limit.get(field)
            if isinstance(candidate, dict):
                return candidate
            if field == "primary_window":
                return rate_limit
        candidate = limit.get(field)
        if isinstance(candidate, dict):
            return candidate
        return None

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

    for item in _additional_limits(data):
        if isinstance(item, dict) and _is_code_review_limit(item):
            return item

    return None


def _extra_usage_limit(data: dict[str, Any]) -> dict[str, Any] | None:
    """Return an additional limit object related to paid flexible usage."""
    for item in _additional_limits(data):
        if not isinstance(item, dict) or _is_code_review_limit(item):
            continue
        if _is_extra_usage_limit(item):
            return item
    return None


def _spark_limit(data: dict[str, Any]) -> dict[str, Any] | None:
    """Return an additional Codex Spark limit object."""
    for item in _additional_limits(data):
        if isinstance(item, dict) and _is_spark_limit(item):
            return item
    return None


def _additional_limits(data: dict[str, Any]) -> tuple[Any, ...]:
    """Return additional rate limit entries."""
    additional_limits = first_present(
        data,
        ("additional_rate_limits",),
        ("rate_limits", "additional_rate_limits"),
    )
    return tuple(additional_limits) if isinstance(additional_limits, list) else ()


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
        if "github_code_review" in normalized:
            continue
        if any(token in normalized for token in ("code_review", "core_review", "auto_review")):
            return True
    return False


def _is_spark_limit(item: dict[str, Any]) -> bool:
    """Return whether an additional limit entry appears to be for Codex Spark."""
    for field in SPARK_LABEL_FIELDS:
        value = item.get(field)
        if not isinstance(value, str):
            continue
        if "spark" in value.lower():
            return True
    return False


def _is_extra_usage_limit(item: dict[str, Any]) -> bool:
    """Return whether an additional limit appears to describe extra usage."""
    if isinstance(item.get("credits"), dict) or isinstance(item.get("spend_control"), dict):
        return True
    if _first_numeric_field(
        item,
        EXTRA_USAGE_CREDIT_FIELDS + EXTRA_USAGE_LIMIT_FIELDS,
    ) is not None:
        return True

    for field in EXTRA_USAGE_LABEL_FIELDS:
        value = item.get(field)
        if not isinstance(value, str):
            continue
        normalized = value.lower().replace("-", "_").replace(" ", "_")
        if any(
            token in normalized
            for token in (
                "extra",
                "credit",
                "flexible",
                "overage",
                "pay_as_you_go",
                "balance",
            )
        ):
            return True
    return False

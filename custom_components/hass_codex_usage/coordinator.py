"""Data coordinator for Codex Usage."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any

from aiohttp import ClientError, ClientResponseError

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .auth_helpers import chatgpt_request_headers
from .const import (
    CODEX_RATE_LIMIT_RESET_CREDITS_URL,
    CODEX_USAGE_URL,
    CONF_UPDATE_INTERVAL,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    USER_AGENT,
)
from .oauth import (
    CodexUsageAuthError,
    CodexUsageConnectionError,
    async_ensure_token_valid,
    async_refresh_entry_token,
)

_LOGGER = logging.getLogger(__name__)
_RESET_CREDIT_DETAIL_FIELDS = (
    "id",
    "reset_type",
    "status",
    "granted_at",
    "expires_at",
    "title",
    "description",
)


def _retry_after_seconds(value: str | None) -> float | None:
    """Parse a Retry-After header."""
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None

    return max(0.0, (retry_at - dt_util.utcnow()).total_seconds())


class CodexUsageCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate Codex usage updates."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.session = async_get_clientsession(hass)
        self.last_success_time: datetime | None = None

        update_interval = entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS
        )

        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
            config_entry=entry,
        )

    def _async_refresh_finished(self) -> None:
        """Track the last successful refresh time."""
        if self.last_update_success:
            self.last_success_time = dt_util.utcnow()

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch the latest Codex usage data."""
        try:
            token = await async_ensure_token_valid(
                self.hass, self.entry, self.session
            )
            return await self._async_fetch_usage(token)
        except CodexUsageAuthError:
            try:
                token = await async_refresh_entry_token(
                    self.hass,
                    self.entry,
                    self.session,
                    force=True,
                )
                return await self._async_fetch_usage(token)
            except CodexUsageAuthError as refresh_err:
                raise ConfigEntryAuthFailed(refresh_err) from refresh_err
            except CodexUsageConnectionError as refresh_err:
                raise UpdateFailed(refresh_err) from refresh_err
        except CodexUsageConnectionError as err:
            raise UpdateFailed(err) from err

    async def _async_fetch_usage(self, token: dict[str, Any]) -> dict[str, Any]:
        """Fetch usage data from ChatGPT."""
        access_token = token.get(CONF_ACCESS_TOKEN)
        if not isinstance(access_token, str) or not access_token:
            raise CodexUsageAuthError("Missing access token")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
            **chatgpt_request_headers(token),
        }

        try:
            async with self.session.get(CODEX_USAGE_URL, headers=headers) as response:
                if response.status == 401:
                    raise CodexUsageAuthError("Codex usage token is invalid")
                if response.status == 429:
                    raise UpdateFailed(
                        "Codex usage endpoint is rate limited",
                        retry_after=_retry_after_seconds(
                            response.headers.get("Retry-After")
                        ),
                    )
                response.raise_for_status()
                data = await response.json(content_type=None)
        except ClientResponseError as err:
            raise CodexUsageConnectionError(
                f"Codex usage request failed with HTTP {err.status}"
            ) from err
        except ClientError as err:
            raise CodexUsageConnectionError("Codex usage request failed") from err
        except ValueError as err:
            raise CodexUsageConnectionError("Codex usage response was not valid JSON") from err

        if not isinstance(data, dict):
            raise CodexUsageConnectionError("Codex usage response was not an object")

        metadata = {
            "api_endpoint": CODEX_USAGE_URL.removeprefix("https://"),
            "account_email": token.get("account_email"),
            "account_id": token.get("account_id"),
        }
        if _has_available_reset_credit(data):
            details = await self._async_fetch_reset_credit_details(headers)
            if details is not None:
                metadata["rate_limit_reset_credits"] = details
        data["_meta"] = metadata

        return data

    async def _async_fetch_reset_credit_details(
        self, headers: dict[str, str]
    ) -> dict[str, Any] | None:
        """Fetch optional reset-credit details without failing usage polling."""
        try:
            async with self.session.get(
                CODEX_RATE_LIMIT_RESET_CREDITS_URL, headers=headers
            ) as response:
                response.raise_for_status()
                details = await response.json(content_type=None)
        except (ClientError, ValueError):
            _LOGGER.debug("Unable to fetch optional rate-limit reset-credit details")
            return None
        return _sanitize_reset_credit_details(details)


def _has_available_reset_credit(data: dict[str, Any]) -> bool:
    """Return whether the usage summary reports a usable reset credit."""
    summary = data.get("rate_limit_reset_credits")
    if not isinstance(summary, dict):
        return False
    available_count = summary.get("available_count")
    return type(available_count) is int and available_count > 0


def _sanitize_reset_credit_details(value: Any) -> dict[str, Any] | None:
    """Allow only current scalar reset-credit detail fields."""
    if not isinstance(value, dict):
        return None
    sanitized: dict[str, Any] = {}
    available_count = value.get("available_count")
    if type(available_count) is int and available_count >= 0:
        sanitized["available_count"] = available_count

    credits = value.get("credits")
    if not isinstance(credits, list):
        return sanitized
    sanitized_credits = []
    for credit in credits:
        if not isinstance(credit, dict):
            continue
        item = {
            field: credit[field]
            for field in _RESET_CREDIT_DETAIL_FIELDS
            if isinstance(credit.get(field), str) and credit[field]
        }
        if item:
            sanitized_credits.append(item)
    if sanitized_credits:
        sanitized["credits"] = sanitized_credits
    return sanitized

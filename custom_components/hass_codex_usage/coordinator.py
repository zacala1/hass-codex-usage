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

from .const import (
    CODEX_USAGE_URLS,
    CONF_TOKEN,
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


def _retry_after_seconds(value: str | None) -> float | None:
    """Parse a Retry-After header."""
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass

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
            CONF_UPDATE_INTERVAL,
            entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS),
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
            return await self._async_fetch_usage(token[CONF_ACCESS_TOKEN])
        except CodexUsageAuthError as err:
            try:
                token = await async_refresh_entry_token(
                    self.hass,
                    self.entry,
                    self.session,
                    force=True,
                )
                return await self._async_fetch_usage(token[CONF_ACCESS_TOKEN])
            except CodexUsageAuthError as refresh_err:
                raise ConfigEntryAuthFailed(refresh_err) from refresh_err
            except CodexUsageConnectionError as refresh_err:
                raise UpdateFailed(refresh_err) from refresh_err
            except Exception as refresh_err:  # noqa: BLE001
                raise UpdateFailed(refresh_err) from refresh_err
        except CodexUsageConnectionError as err:
            raise UpdateFailed(err) from err

    async def _async_fetch_usage(self, access_token: str) -> dict[str, Any]:
        """Fetch usage data from ChatGPT."""
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        }

        last_error: CodexUsageConnectionError | None = None

        try:
            for index, usage_url in enumerate(CODEX_USAGE_URLS):
                async with self.session.get(usage_url, headers=headers) as response:
                    if response.status == 401:
                        raise CodexUsageAuthError("Codex usage token is invalid")
                    if response.status == 429:
                        raise UpdateFailed(
                            "Codex usage endpoint is rate limited",
                            retry_after=_retry_after_seconds(
                                response.headers.get("Retry-After")
                            ),
                        )
                    if response.status == 404 and index < len(CODEX_USAGE_URLS) - 1:
                        last_error = CodexUsageConnectionError(
                            f"Codex usage endpoint not found: {usage_url}"
                        )
                        continue

                    response.raise_for_status()
                    data = await response.json(content_type=None)
                    break
            else:
                raise last_error or CodexUsageConnectionError(
                    "No Codex usage endpoint succeeded"
                )
        except ClientResponseError as err:
            raise CodexUsageConnectionError(
                f"Codex usage request failed with HTTP {err.status}"
            ) from err
        except ClientError as err:
            raise CodexUsageConnectionError("Codex usage request failed") from err

        if not isinstance(data, dict):
            raise CodexUsageConnectionError("Codex usage response was not an object")

        token_data = self.entry.data.get(CONF_TOKEN, {})
        account_email = data.get("account_email") or data.get("email")
        if isinstance(token_data, dict) and token_data.get("account_email"):
            account_email = token_data["account_email"]

        data["_meta"] = {
            "api_endpoint": usage_url.removeprefix("https://"),
            "account_email": account_email,
        }

        return data

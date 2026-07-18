"""OAuth helpers for Codex Usage."""

from __future__ import annotations

from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant

from .auth_helpers import (
    OPENAI_OAUTH_CLIENT_ID,
    OPENAI_REDIRECT_URI,
    OPENAI_TOKEN_URL,
    normalize_token,
    token_needs_refresh,
)
from .const import (
    CONF_REFRESH_TOKEN,
    CONF_TOKEN,
)


class CodexUsageError(Exception):
    """Base exception for Codex Usage."""


class CodexUsageAuthError(CodexUsageError):
    """Raised when authentication fails."""


class CodexUsageConnectionError(CodexUsageError):
    """Raised when a request cannot be completed."""


async def async_exchange_code_for_token(
    session: ClientSession,
    authorization_code: str,
    code_verifier: str,
) -> dict[str, Any]:
    """Exchange an authorization code for an OAuth token."""
    payload = {
        "grant_type": "authorization_code",
        "client_id": OPENAI_OAUTH_CLIENT_ID,
        "code": authorization_code.strip(),
        "redirect_uri": OPENAI_REDIRECT_URI,
        "code_verifier": code_verifier,
    }
    return await _async_request_token(session, payload)


async def async_ensure_token_valid(
    hass: HomeAssistant,
    entry: ConfigEntry,
    session: ClientSession,
) -> dict[str, Any]:
    """Return a valid access token, refreshing it when needed."""
    token = entry.data.get(CONF_TOKEN, {})
    if not isinstance(token, dict) or not token.get(CONF_ACCESS_TOKEN):
        raise CodexUsageAuthError("Missing access token")

    if not token_needs_refresh(token):
        return token

    return await async_refresh_entry_token(hass, entry, session)


async def async_refresh_entry_token(
    hass: HomeAssistant,
    entry: ConfigEntry,
    session: ClientSession,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Refresh a config entry OAuth token and persist it."""
    token = entry.data.get(CONF_TOKEN, {})
    if not isinstance(token, dict):
        raise CodexUsageAuthError("Missing token data")

    refresh_token = token.get(CONF_REFRESH_TOKEN)
    if not refresh_token:
        raise CodexUsageAuthError("Missing refresh token")

    if not force:
        if not token_needs_refresh(token):
            return token

    new_token = await _async_request_token(
        session,
        {
            "grant_type": "refresh_token",
            "client_id": OPENAI_OAUTH_CLIENT_ID,
            "refresh_token": refresh_token,
        },
        previous_token=token,
    )

    new_data = {**entry.data, CONF_TOKEN: new_token}
    hass.config_entries.async_update_entry(entry, data=new_data)
    return new_token


async def _async_request_token(
    session: ClientSession,
    payload: dict[str, Any],
    *,
    previous_token: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Request a token from the OAuth token endpoint."""
    try:
        async with session.post(
            OPENAI_TOKEN_URL,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ) as response:
            if response.status in {400, 401, 403}:
                raise CodexUsageAuthError("OpenAI rejected the OAuth request")
            response.raise_for_status()
            token = await response.json(content_type=None)
    except CodexUsageAuthError:
        raise
    except ClientResponseError as err:
        raise CodexUsageConnectionError(
            f"OpenAI token request failed with HTTP {err.status}"
        ) from err
    except ClientError as err:
        raise CodexUsageConnectionError("OpenAI token request failed") from err

    if not isinstance(token, dict) or CONF_ACCESS_TOKEN not in token:
        raise CodexUsageAuthError("OpenAI token response did not include access_token")

    return normalize_token(token, previous_token=previous_token)

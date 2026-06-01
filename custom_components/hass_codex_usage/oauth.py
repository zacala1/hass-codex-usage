"""OAuth helpers for Codex Usage."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
import time
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant

from .auth_helpers import (
    OPENAI_DEVICE_REDIRECT_URI,
    OPENAI_DEVICE_TOKEN_URL,
    OPENAI_DEVICE_USER_CODE_URL,
    OPENAI_DEVICE_VERIFICATION_URL,
    build_authorization_url,
    create_pkce_pair,
    create_state,
    normalize_token,
    parse_authorization_response,
    seconds_value,
    token_needs_refresh,
)
from .const import (
    CONF_EXPIRES_AT,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN,
    OPENAI_OAUTH_CLIENT_ID,
    OPENAI_REDIRECT_URI,
    OPENAI_TOKEN_URL,
)


DEVICE_AUTH_TIMEOUT_SECONDS = 15 * 60
DEFAULT_DEVICE_AUTH_POLL_INTERVAL_SECONDS = 5.0


@dataclass(frozen=True, kw_only=True)
class CodexDeviceCode:
    """Device-code authorization details shown to the user."""

    verification_url: str
    user_code: str
    device_auth_id: str
    interval: float


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


async def async_request_device_code(session: ClientSession) -> CodexDeviceCode:
    """Request a Codex device-code login challenge."""
    try:
        async with session.post(
            OPENAI_DEVICE_USER_CODE_URL,
            json={"client_id": OPENAI_OAUTH_CLIENT_ID},
            headers={"Content-Type": "application/json"},
        ) as response:
            if response.status in {400, 401, 403, 404}:
                raise CodexUsageAuthError("OpenAI rejected the device-code request")
            response.raise_for_status()
            data = await response.json(content_type=None)
    except CodexUsageAuthError:
        raise
    except ClientResponseError as err:
        raise CodexUsageConnectionError(
            f"OpenAI device-code request failed with HTTP {err.status}"
        ) from err
    except ClientError as err:
        raise CodexUsageConnectionError("OpenAI device-code request failed") from err
    except ValueError as err:
        raise CodexUsageConnectionError(
            "OpenAI device-code response was not valid JSON"
        ) from err

    if not isinstance(data, dict):
        raise CodexUsageAuthError("OpenAI device-code response was not an object")

    user_code = data.get("user_code") or data.get("usercode")
    device_auth_id = data.get("device_auth_id")
    if not isinstance(user_code, str) or not user_code:
        raise CodexUsageAuthError("OpenAI device-code response missing user_code")
    if not isinstance(device_auth_id, str) or not device_auth_id:
        raise CodexUsageAuthError("OpenAI device-code response missing device_auth_id")

    interval = seconds_value(data.get("interval"))
    if interval is None or interval <= 0:
        interval = DEFAULT_DEVICE_AUTH_POLL_INTERVAL_SECONDS

    return CodexDeviceCode(
        verification_url=OPENAI_DEVICE_VERIFICATION_URL,
        user_code=user_code,
        device_auth_id=device_auth_id,
        interval=interval,
    )


async def async_exchange_device_code_for_token(
    session: ClientSession,
    device_code: CodexDeviceCode,
) -> dict[str, Any]:
    """Wait for device-code authorization and exchange it for OAuth tokens."""
    authorization = await _async_poll_device_authorization(session, device_code)
    authorization_code = authorization.get("authorization_code")
    code_verifier = authorization.get("code_verifier")

    if not isinstance(authorization_code, str) or not authorization_code:
        raise CodexUsageAuthError(
            "OpenAI device authorization response missing authorization_code"
        )
    if not isinstance(code_verifier, str) or not code_verifier:
        raise CodexUsageAuthError(
            "OpenAI device authorization response missing code_verifier"
        )

    payload = {
        "grant_type": "authorization_code",
        "client_id": OPENAI_OAUTH_CLIENT_ID,
        "code": authorization_code,
        "redirect_uri": OPENAI_DEVICE_REDIRECT_URI,
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


async def _async_poll_device_authorization(
    session: ClientSession,
    device_code: CodexDeviceCode,
) -> dict[str, Any]:
    """Poll until OpenAI issues an authorization code for the device login."""
    deadline = time.monotonic() + DEVICE_AUTH_TIMEOUT_SECONDS

    while True:
        try:
            async with session.post(
                OPENAI_DEVICE_TOKEN_URL,
                json={
                    "device_auth_id": device_code.device_auth_id,
                    "user_code": device_code.user_code,
                },
                headers={"Content-Type": "application/json"},
            ) as response:
                if response.status < 400:
                    data = await response.json(content_type=None)
                    if isinstance(data, dict):
                        return data
                    raise CodexUsageAuthError(
                        "OpenAI device authorization response was not an object"
                    )

                if response.status in {403, 404}:
                    if time.monotonic() >= deadline:
                        raise CodexUsageAuthError("OpenAI device authorization timed out")
                    await asyncio.sleep(
                        min(
                            device_code.interval,
                            max(0.0, deadline - time.monotonic()),
                        )
                    )
                    continue

                if response.status in {400, 401}:
                    raise CodexUsageAuthError(
                        "OpenAI rejected the device authorization"
                    )

                response.raise_for_status()
        except CodexUsageAuthError:
            raise
        except ClientResponseError as err:
            raise CodexUsageConnectionError(
                f"OpenAI device authorization failed with HTTP {err.status}"
            ) from err
        except ClientError as err:
            raise CodexUsageConnectionError(
                "OpenAI device authorization request failed"
            ) from err
        except ValueError as err:
            raise CodexUsageConnectionError(
                "OpenAI device authorization response was not valid JSON"
            ) from err


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

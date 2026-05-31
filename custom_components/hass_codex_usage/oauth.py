"""OAuth helpers for Codex Usage."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

from aiohttp import ClientError, ClientResponseError, ClientSession

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant

from .const import (
    CONF_EXPIRES_AT,
    CONF_REFRESH_TOKEN,
    CONF_TOKEN,
    CONF_TOKEN_TYPE,
    OPENAI_AUTHORIZATION_URL,
    OPENAI_AUTH_EXTRA_PARAMS,
    OPENAI_CODE_CHALLENGE_METHOD,
    OPENAI_OAUTH_CLIENT_ID,
    OPENAI_OAUTH_SCOPE,
    OPENAI_REDIRECT_URI,
    OPENAI_TOKEN_URL,
    TOKEN_REFRESH_MARGIN_SECONDS,
)


class CodexUsageError(Exception):
    """Base exception for Codex Usage."""


class CodexUsageAuthError(CodexUsageError):
    """Raised when authentication fails."""


class CodexUsageConnectionError(CodexUsageError):
    """Raised when a request cannot be completed."""


def create_pkce_pair() -> tuple[str, str]:
    """Create a PKCE code verifier and S256 challenge."""
    verifier_text = secrets.token_urlsafe(64)
    challenge_digest = hashlib.sha256(verifier_text.encode()).digest()
    challenge = base64.urlsafe_b64encode(challenge_digest).decode().rstrip("=")
    return verifier_text, challenge


def create_state() -> str:
    """Create an OAuth state value."""
    return secrets.token_urlsafe(32)


def build_authorization_url(code_challenge: str, state: str) -> str:
    """Build the OpenAI authorization URL."""
    query = {
        "response_type": "code",
        "client_id": OPENAI_OAUTH_CLIENT_ID,
        "redirect_uri": OPENAI_REDIRECT_URI,
        "scope": OPENAI_OAUTH_SCOPE,
        "code_challenge": code_challenge,
        "code_challenge_method": OPENAI_CODE_CHALLENGE_METHOD,
        "state": state,
        **OPENAI_AUTH_EXTRA_PARAMS,
    }
    return f"{OPENAI_AUTHORIZATION_URL}?{urlencode(query)}"


def parse_authorization_response(value: str) -> tuple[str, str | None]:
    """Extract authorization code and optional state from a code or redirect URL."""
    candidate = value.strip()
    parsed = urlparse(candidate)
    if parsed.query:
        query = parse_qs(parsed.query)
        code_values = query.get("code")
        if code_values:
            state_values = query.get("state")
            return code_values[0], state_values[0] if state_values else None

    return candidate, None


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

    expires_at = float(token.get(CONF_EXPIRES_AT, 0))
    if expires_at - time.time() > TOKEN_REFRESH_MARGIN_SECONDS:
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
        expires_at = float(token.get(CONF_EXPIRES_AT, 0))
        if expires_at - time.time() > TOKEN_REFRESH_MARGIN_SECONDS:
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
        async with session.post(OPENAI_TOKEN_URL, data=payload) as response:
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

    return _normalize_token(token, previous_token=previous_token)


def _normalize_token(
    token: dict[str, Any],
    *,
    previous_token: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize token fields for storage."""
    normalized = dict(token)
    previous_token = previous_token or {}

    if CONF_REFRESH_TOKEN not in normalized and previous_token.get(CONF_REFRESH_TOKEN):
        normalized[CONF_REFRESH_TOKEN] = previous_token[CONF_REFRESH_TOKEN]

    expires_in = normalized.get("expires_in")
    if expires_in is not None and CONF_EXPIRES_AT not in normalized:
        normalized[CONF_EXPIRES_AT] = time.time() + int(expires_in)

    normalized.setdefault(CONF_TOKEN_TYPE, "Bearer")

    account_email = _email_from_id_token(normalized.get("id_token"))
    if account_email:
        normalized["account_email"] = account_email
    elif previous_token.get("account_email"):
        normalized["account_email"] = previous_token["account_email"]

    return normalized


def _email_from_id_token(id_token: Any) -> str | None:
    """Extract email from an ID token without validating the signature."""
    if not isinstance(id_token, str):
        return None

    parts = id_token.split(".")
    if len(parts) < 2:
        return None

    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload)
        claims = json.loads(decoded)
    except (ValueError, json.JSONDecodeError):
        return None

    email = claims.get("email")
    return email if isinstance(email, str) else None

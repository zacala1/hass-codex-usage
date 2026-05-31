"""Pure OAuth helpers for Codex Usage."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

OPENAI_OAUTH_CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
OPENAI_AUTHORIZATION_URL = "https://auth.openai.com/oauth/authorize"
OPENAI_TOKEN_URL = "https://auth.openai.com/oauth/token"
OPENAI_REDIRECT_URI = "http://localhost:1455/auth/callback"
OPENAI_OAUTH_SCOPE = (
    "openid profile email offline_access "
    "api.connectors.read api.connectors.invoke"
)
OPENAI_CODE_CHALLENGE_METHOD = "S256"
OPENAI_AUTH_EXTRA_PARAMS = {
    "id_token_add_organizations": "true",
    "codex_cli_simplified_flow": "true",
    "originator": "codex_cli_rs",
}


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


def normalize_token(
    token: dict[str, Any],
    *,
    previous_token: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize token fields for storage."""
    normalized = dict(token)
    previous_token = previous_token or {}

    if "refresh_token" not in normalized and previous_token.get("refresh_token"):
        normalized["refresh_token"] = previous_token["refresh_token"]

    expires_in = normalized.get("expires_in")
    if expires_in is not None and "expires_at" not in normalized:
        normalized["expires_at"] = time.time() + int(expires_in)

    normalized.setdefault("token_type", "Bearer")

    account_email = email_from_id_token(normalized.get("id_token"))
    if account_email:
        normalized["account_email"] = account_email
    elif previous_token.get("account_email"):
        normalized["account_email"] = previous_token["account_email"]

    return normalized


def email_from_id_token(id_token: Any) -> str | None:
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

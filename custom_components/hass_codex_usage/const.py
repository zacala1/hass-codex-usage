"""Constants for the Codex Usage integration."""

from __future__ import annotations

from homeassistant.const import CONF_ACCESS_TOKEN

from .auth_helpers import (
    OPENAI_AUTH_EXTRA_PARAMS,
    OPENAI_AUTHORIZATION_URL,
    OPENAI_CODE_CHALLENGE_METHOD,
    OPENAI_OAUTH_CLIENT_ID,
    OPENAI_OAUTH_SCOPE,
    OPENAI_REDIRECT_URI,
    OPENAI_TOKEN_URL,
)

DOMAIN = "hass_codex_usage"
DEFAULT_NAME = "Codex Usage"
VERSION = "0.1.0"

CONF_AUTHORIZATION_CODE = "authorization_code"
CONF_EXPIRES_AT = "expires_at"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_TOKEN = "token"
CONF_TOKEN_TYPE = "token_type"
CONF_UPDATE_INTERVAL = "update_interval"

CODEX_USAGE_URLS = (
    "https://chatgpt.com/backend-api/api/codex/usage",
    "https://chatgpt.com/backend-api/codex/usage",
)
CODEX_USAGE_ENDPOINT_LABEL = "chatgpt.com/backend-api/api/codex/usage"
USER_AGENT = f"HomeAssistant/hass-codex-usage/{VERSION}"

DEFAULT_SCAN_INTERVAL_SECONDS = 300
MIN_SCAN_INTERVAL_SECONDS = 60
MAX_SCAN_INTERVAL_SECONDS = 3600
TOKEN_REFRESH_MARGIN_SECONDS = 300

TOKEN_KEYS = {
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_EXPIRES_AT,
    CONF_TOKEN_TYPE,
    "id_token",
    "account_email",
}

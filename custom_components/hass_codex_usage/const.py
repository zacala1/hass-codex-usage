"""Constants for the Codex Usage integration."""

from __future__ import annotations

from homeassistant.const import CONF_ACCESS_TOKEN

DOMAIN = "hass_codex_usage"
DEFAULT_NAME = "Codex Usage"
VERSION = "0.1.0"

CONF_AUTHORIZATION_CODE = "authorization_code"
CONF_EXPIRES_AT = "expires_at"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_TOKEN = "token"
CONF_TOKEN_TYPE = "token_type"
CONF_UPDATE_INTERVAL = "update_interval"

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

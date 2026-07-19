"""Constants for the Codex Usage integration."""

from __future__ import annotations

DOMAIN = "hass_codex_usage"
DEFAULT_NAME = "Codex Usage"
VERSION = "0.3.2"

CONF_AUTHORIZATION_CODE = "authorization_code"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_TOKEN = "token"
CONF_UPDATE_INTERVAL = "update_interval"

CODEX_USAGE_URL = "https://chatgpt.com/backend-api/wham/usage"
CODEX_RATE_LIMIT_RESET_CREDITS_URL = (
    "https://chatgpt.com/backend-api/wham/rate-limit-reset-credits"
)
CODEX_USAGE_ENDPOINT_LABEL = "chatgpt.com/backend-api/wham/usage"
USER_AGENT = f"HomeAssistant/hass-codex-usage/{VERSION}"

DEFAULT_SCAN_INTERVAL_SECONDS = 300
MIN_SCAN_INTERVAL_SECONDS = 60
MAX_SCAN_INTERVAL_SECONDS = 3600

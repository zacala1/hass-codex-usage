"""Config flow for Codex Usage."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .auth_helpers import (
    build_authorization_url,
    create_pkce_pair,
    create_state,
    parse_authorization_response,
    token_unique_id,
)
from .const import (
    CONF_AUTHORIZATION_CODE,
    CONF_TOKEN,
    CONF_UPDATE_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    MAX_SCAN_INTERVAL_SECONDS,
    MIN_SCAN_INTERVAL_SECONDS,
)
from .oauth import (
    CodexUsageAuthError,
    CodexUsageConnectionError,
    async_exchange_code_for_token,
)


def _auth_schema() -> vol.Schema:
    """Return the auth form schema."""
    return vol.Schema({vol.Required(CONF_AUTHORIZATION_CODE): str})


class CodexUsageConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Codex Usage."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._code_verifier: str | None = None
        self._auth_url: str | None = None
        self._state: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return CodexUsageOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial OAuth login step."""
        errors: dict[str, str] = {}

        self._ensure_authorization_url()

        if user_input is not None:
            token = await self._async_exchange_user_input(user_input, errors)
            if token is not None:
                return await self._async_finish_token(token)

        return self._show_auth_form("user", errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle reauthentication with a new OAuth code."""
        errors: dict[str, str] = {}

        self._ensure_authorization_url()

        if user_input is not None:
            token = await self._async_exchange_user_input(user_input, errors)
            if token is not None:
                return await self._async_finish_token(token)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_auth_schema(),
            description_placeholders=self._auth_description_placeholders(),
            errors=errors,
        )

    def _ensure_authorization_url(self) -> None:
        """Generate the OAuth URL once for the current flow."""
        if self._code_verifier is not None and self._auth_url is not None:
            return

        self._code_verifier, code_challenge = create_pkce_pair()
        self._state = create_state()
        self._auth_url = build_authorization_url(code_challenge, self._state)

    async def _async_exchange_user_input(
        self,
        user_input: dict[str, Any],
        errors: dict[str, str],
    ) -> dict[str, Any] | None:
        """Exchange the pasted authorization response for an OAuth token."""
        authorization_response = user_input.get(CONF_AUTHORIZATION_CODE, "").strip()
        if not authorization_response:
            errors[CONF_AUTHORIZATION_CODE] = "missing_code"
            return None

        try:
            authorization_code, returned_state = parse_authorization_response(
                authorization_response
            )
            if returned_state is not None and returned_state != self._state:
                raise CodexUsageAuthError("OAuth state did not match")

            session = async_get_clientsession(self.hass)
            return await async_exchange_code_for_token(
                session,
                authorization_code,
                self._code_verifier,
            )
        except CodexUsageAuthError:
            errors["base"] = "invalid_auth"
        except CodexUsageConnectionError:
            errors["base"] = "cannot_connect"
        except Exception:  # noqa: BLE001
            errors["base"] = "unknown"

        return None

    async def _async_finish_token(self, token: dict[str, Any]) -> FlowResult:
        """Create or update a config entry from a normalized OAuth token."""
        unique_id = token_unique_id(token, DOMAIN)

        if self.source == config_entries.SOURCE_REAUTH:
            reauth_entry = self._get_reauth_entry()
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_mismatch()
            return self.async_update_reload_and_abort(
                reauth_entry,
                unique_id=unique_id,
                data_updates={CONF_TOKEN: token},
            )

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=self._title_from_token(token),
            data={CONF_TOKEN: token},
            options={CONF_UPDATE_INTERVAL: DEFAULT_SCAN_INTERVAL_SECONDS},
        )

    def _show_auth_form(
        self,
        step_id: str,
        errors: dict[str, str],
    ) -> FlowResult:
        """Show the OAuth form with the current authorization URL."""
        return self.async_show_form(
            step_id=step_id,
            data_schema=_auth_schema(),
            description_placeholders=self._auth_description_placeholders(),
            errors=errors,
        )

    def _auth_description_placeholders(self) -> dict[str, str]:
        """Return the OAuth link placeholder."""
        return {"url": self._auth_url or ""}

    def _title_from_token(self, token: dict[str, Any]) -> str:
        """Return a user-facing title for a new config entry."""
        account_email = token.get("account_email")
        if isinstance(account_email, str):
            return f"{DEFAULT_NAME} ({account_email})"
        account_id = token.get("account_id")
        if isinstance(account_id, str):
            return f"{DEFAULT_NAME} ({account_id})"
        return DEFAULT_NAME


class CodexUsageOptionsFlow(config_entries.OptionsFlowWithReload):
    """Handle Codex Usage options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_UPDATE_INTERVAL,
                        default=current_interval,
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(
                            min=MIN_SCAN_INTERVAL_SECONDS,
                            max=MAX_SCAN_INTERVAL_SECONDS,
                        ),
                    ),
                }
            ),
        )

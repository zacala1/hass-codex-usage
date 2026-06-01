"""Config flow for Codex Usage."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .auth_helpers import reauth_unique_id
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
    build_authorization_url,
    create_pkce_pair,
    create_state,
    parse_authorization_response,
)


def _auth_schema(include_setup_fields: bool, current_interval: int) -> vol.Schema:
    """Return the auth form schema."""
    schema: dict[Any, Any] = {
        vol.Required(CONF_AUTHORIZATION_CODE): str,
    }

    if include_setup_fields:
        schema.update(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
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
        )

    return vol.Schema(schema)


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
        """Handle the initial step."""
        errors: dict[str, str] = {}
        include_setup_fields = self.source != config_entries.SOURCE_REAUTH

        if self._code_verifier is None or self._auth_url is None:
            self._code_verifier, code_challenge = create_pkce_pair()
            self._state = create_state()
            self._auth_url = build_authorization_url(code_challenge, self._state)

        if user_input is not None:
            try:
                authorization_code, returned_state = parse_authorization_response(
                    user_input[CONF_AUTHORIZATION_CODE]
                )
                if returned_state is not None and returned_state != self._state:
                    raise CodexUsageAuthError("OAuth state did not match")

                session = async_get_clientsession(self.hass)
                token = await async_exchange_code_for_token(
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
            else:
                account_email = token.get("account_email")
                unique_id = account_email or DOMAIN

                if self.source == config_entries.SOURCE_REAUTH:
                    reauth_entry = self._get_reauth_entry()
                    unique_id, enforce_mismatch = reauth_unique_id(
                        reauth_entry.unique_id,
                        account_email,
                        DOMAIN,
                    )
                    await self.async_set_unique_id(unique_id)
                    if enforce_mismatch:
                        self._abort_if_unique_id_mismatch()
                    return self.async_update_reload_and_abort(
                        reauth_entry,
                        unique_id=unique_id,
                        data_updates={CONF_TOKEN: token},
                    )

                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_TOKEN: token,
                        CONF_UPDATE_INTERVAL: user_input[CONF_UPDATE_INTERVAL],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_auth_schema(
                include_setup_fields,
                DEFAULT_SCAN_INTERVAL_SECONDS,
            ),
            description_placeholders={"auth_url": self._auth_url},
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Handle reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm reauthentication before showing a new OAuth URL."""
        if user_input is not None:
            return await self.async_step_user()

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({}),
        )


class CodexUsageOptionsFlow(config_entries.OptionsFlowWithReload):
    """Handle Codex Usage options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL,
            self.config_entry.data.get(
                CONF_UPDATE_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS
            ),
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

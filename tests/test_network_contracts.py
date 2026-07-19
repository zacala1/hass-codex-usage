"""Tests for current Codex OAuth and backend request contracts."""

from __future__ import annotations

from collections.abc import Mapping
import importlib.util
from pathlib import Path
import sys
import types
from typing import Any
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION_DIR = ROOT / "custom_components" / "hass_codex_usage"


class StubClientError(Exception):
    """Minimal aiohttp base error for dependency-free contract tests."""


class StubClientResponseError(StubClientError):
    """Minimal response error carrying the HTTP status used by runtime code."""

    def __init__(self, status: int) -> None:
        """Store the failing response status."""
        super().__init__(f"HTTP {status}")
        self.status = status


class StubClientSession:
    """Minimal aiohttp session type used only by runtime annotations."""


class StubDataUpdateCoordinator:
    """Minimal generic-compatible coordinator base for dependency-free tests."""

    @classmethod
    def __class_getitem__(cls, item: Any) -> type[StubDataUpdateCoordinator]:
        """Support the runtime class subscription used by the integration."""
        return cls


class StubUpdateFailed(Exception):
    """Minimal Home Assistant update error."""

    def __init__(self, *args: Any, retry_after: float | None = None) -> None:
        """Store the optional retry delay used by the coordinator."""
        super().__init__(*args)
        self.retry_after = retry_after


def _load_module(module_name: str, path: Path) -> types.ModuleType:
    specification = importlib.util.spec_from_file_location(module_name, path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


def _load_runtime_modules() -> tuple[types.ModuleType, types.ModuleType]:
    """Load OAuth and coordinator modules with small Home Assistant stubs."""
    package_name = "hass_codex_usage_network_test"
    package = types.ModuleType(package_name)
    package.__path__ = [str(INTEGRATION_DIR)]

    homeassistant = types.ModuleType("homeassistant")
    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = type("ConfigEntry", (), {})
    ha_const = types.ModuleType("homeassistant.const")
    ha_const.CONF_ACCESS_TOKEN = "access_token"
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = type("HomeAssistant", (), {})
    exceptions = types.ModuleType("homeassistant.exceptions")
    exceptions.ConfigEntryAuthFailed = type(
        "ConfigEntryAuthFailed", (Exception,), {}
    )
    helpers = types.ModuleType("homeassistant.helpers")
    aiohttp_client = types.ModuleType("homeassistant.helpers.aiohttp_client")
    aiohttp_client.async_get_clientsession = lambda hass: None
    update_coordinator = types.ModuleType(
        "homeassistant.helpers.update_coordinator"
    )
    update_coordinator.DataUpdateCoordinator = StubDataUpdateCoordinator
    update_coordinator.UpdateFailed = StubUpdateFailed
    util = types.ModuleType("homeassistant.util")
    dt = types.ModuleType("homeassistant.util.dt")
    dt.utcnow = lambda: None
    util.dt = dt
    aiohttp = types.ModuleType("aiohttp")
    aiohttp.ClientError = StubClientError
    aiohttp.ClientResponseError = StubClientResponseError
    aiohttp.ClientSession = StubClientSession

    stub_modules = {
        package_name: package,
        "aiohttp": aiohttp,
        "homeassistant": homeassistant,
        "homeassistant.config_entries": config_entries,
        "homeassistant.const": ha_const,
        "homeassistant.core": core,
        "homeassistant.exceptions": exceptions,
        "homeassistant.helpers": helpers,
        "homeassistant.helpers.aiohttp_client": aiohttp_client,
        "homeassistant.helpers.update_coordinator": update_coordinator,
        "homeassistant.util": util,
        "homeassistant.util.dt": dt,
    }
    with mock.patch.dict(sys.modules, stub_modules):
        _load_module(
            f"{package_name}.auth_helpers",
            INTEGRATION_DIR / "auth_helpers.py",
        )
        _load_module(f"{package_name}.const", INTEGRATION_DIR / "const.py")
        oauth = _load_module(f"{package_name}.oauth", INTEGRATION_DIR / "oauth.py")
        coordinator = _load_module(
            f"{package_name}.coordinator",
            INTEGRATION_DIR / "coordinator.py",
        )
    return oauth, coordinator


OAUTH, COORDINATOR = _load_runtime_modules()


class FakeResponse:
    """Async response context that returns one predefined JSON object."""

    def __init__(
        self,
        payload: Any,
        *,
        status: int = 200,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.payload = payload
        self.status = status
        self.headers = dict(headers or {})

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        return None

    def raise_for_status(self) -> None:
        if self.status >= 400:
            raise StubClientResponseError(self.status)

    async def json(self, *, content_type: None = None) -> Any:
        return self.payload


class FakeSession:
    """Capture aiohttp request arguments and return queued responses."""

    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append(("POST", url, kwargs))
        return self.responses.pop(0)

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append(("GET", url, kwargs))
        return self.responses.pop(0)


class FakeConfigEntries:
    """Capture Home Assistant config-entry persistence."""

    def __init__(self) -> None:
        self.updated_data: dict[str, Any] | None = None

    def async_update_entry(self, entry: Any, *, data: dict[str, Any]) -> None:
        self.updated_data = data


class NetworkContractTest(unittest.IsolatedAsyncioTestCase):
    """Test wire-adjacent request arguments without real credentials."""

    async def test_authorization_code_exchange_posts_form_data(self) -> None:
        # Given: a successful token endpoint response.
        session = FakeSession([FakeResponse({"access_token": "access"})])

        # When: the integration exchanges an authorization code.
        await OAUTH.async_exchange_code_for_token(session, "code", "verifier")

        # Then: Codex's authorization-code contract remains form encoded.
        method, _, kwargs = session.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(kwargs["data"]["grant_type"], "authorization_code")
        self.assertNotIn("json", kwargs)
        self.assertEqual(
            kwargs["headers"]["Content-Type"],
            "application/x-www-form-urlencoded",
        )

    async def test_refresh_token_exchange_posts_json(self) -> None:
        # Given: an entry whose refresh token can be exchanged successfully.
        session = FakeSession(
            [FakeResponse({"access_token": "new-access", "expires_in": 3600})]
        )
        entry = types.SimpleNamespace(
            data={"token": {"access_token": "old", "refresh_token": "refresh"}}
        )
        config_entries = FakeConfigEntries()
        hass = types.SimpleNamespace(config_entries=config_entries)

        # When: the integration forces a token refresh.
        await OAUTH.async_refresh_entry_token(hass, entry, session, force=True)

        # Then: current Codex refresh semantics use a JSON request body.
        method, _, kwargs = session.calls[0]
        self.assertEqual(method, "POST")
        self.assertEqual(kwargs["json"]["grant_type"], "refresh_token")
        self.assertEqual(kwargs["json"]["refresh_token"], "refresh")
        self.assertNotIn("data", kwargs)
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")

    async def test_usage_requests_include_account_routing_and_reset_details(self) -> None:
        # Given: a FedRAMP account with available rate-limit reset credits.
        session = FakeSession(
            [
                FakeResponse({"rate_limit_reset_credits": {"available_count": 1}}),
                FakeResponse(
                    {
                        "available_count": 1,
                        "credits": [
                            {
                                "id": "credit-1",
                                "reset_type": "codex_rate_limits",
                                "status": "available",
                                "granted_at": "2026-06-18T00:00:00Z",
                                "expires_at": None,
                                "unexpected": "ignored",
                            }
                        ],
                    }
                ),
            ]
        )
        token = {
            "access_token": "access",
            "account_id": "account-123",
            "chatgpt_account_is_fedramp": True,
        }
        coordinator = object.__new__(COORDINATOR.CodexUsageCoordinator)
        coordinator.session = session
        coordinator.entry = types.SimpleNamespace(data={"token": token})

        # When: usage data is fetched.
        data = await coordinator._async_fetch_usage(token)

        # Then: both backend requests carry the selected-account routing headers.
        self.assertEqual(len(session.calls), 2)
        for method, _, kwargs in session.calls:
            self.assertEqual(method, "GET")
            self.assertEqual(kwargs["headers"]["Authorization"], "Bearer access")
            self.assertEqual(
                kwargs["headers"]["ChatGPT-Account-ID"], "account-123"
            )
            self.assertEqual(kwargs["headers"]["X-OpenAI-Fedramp"], "true")
        self.assertEqual(
            data["_meta"]["rate_limit_reset_credits"]["available_count"],
            1,
        )
        self.assertNotIn(
            "unexpected",
            data["_meta"]["rate_limit_reset_credits"]["credits"][0],
        )

    async def test_reset_credit_detail_failure_keeps_usage_summary(self) -> None:
        # Given: usage succeeds but the optional detail endpoint fails.
        session = FakeSession(
            [
                FakeResponse({"rate_limit_reset_credits": {"available_count": 2}}),
                FakeResponse({}, status=500),
            ]
        )
        token = {"access_token": "access", "account_id": "account-123"}
        coordinator = object.__new__(COORDINATOR.CodexUsageCoordinator)
        coordinator.session = session
        coordinator.entry = types.SimpleNamespace(data={"token": token})

        # When: the optional detail request fails.
        data = await coordinator._async_fetch_usage(token)

        # Then: the required usage response remains available without details.
        self.assertEqual(
            data["rate_limit_reset_credits"]["available_count"],
            2,
        )
        self.assertNotIn("rate_limit_reset_credits", data["_meta"])


if __name__ == "__main__":
    unittest.main()

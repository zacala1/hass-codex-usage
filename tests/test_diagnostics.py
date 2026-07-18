"""Tests for Home Assistant diagnostics privacy."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
DIAGNOSTICS_PATH = (
    ROOT / "custom_components" / "hass_codex_usage" / "diagnostics.py"
)
HOME_ASSISTANT_AVAILABLE = importlib.util.find_spec("homeassistant") is not None

if HOME_ASSISTANT_AVAILABLE:
    sys.path.insert(0, str(ROOT))
    try:
        from custom_components.hass_codex_usage.diagnostics import (
            async_get_config_entry_diagnostics,
        )
    finally:
        sys.path.remove(str(ROOT))


def _redact_data(data: Any, keys: set[str]) -> Any:
    """Implement the Home Assistant recursive redaction contract for CI tests."""
    if isinstance(data, Mapping):
        return {
            key: "**REDACTED**" if key in keys else _redact_data(value, keys)
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [_redact_data(value, keys) for value in data]
    return data


def _load_diagnostics_with_homeassistant_stubs() -> types.ModuleType:
    """Load diagnostics without installing the full Home Assistant package."""
    package_name = "hass_codex_usage_diagnostics_test"
    package = types.ModuleType(package_name)
    package.__path__ = [str(DIAGNOSTICS_PATH.parent)]

    const_module = types.ModuleType(f"{package_name}.const")
    const_module.CONF_TOKEN = "token"

    homeassistant = types.ModuleType("homeassistant")
    components = types.ModuleType("homeassistant.components")
    diagnostics_module = types.ModuleType("homeassistant.components.diagnostics")
    diagnostics_module.async_redact_data = _redact_data
    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = type("ConfigEntry", (), {})
    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = type("HomeAssistant", (), {})

    module_name = f"{package_name}.diagnostics"
    specification = importlib.util.spec_from_file_location(module_name, DIAGNOSTICS_PATH)
    assert specification is not None
    assert specification.loader is not None

    stub_modules = {
        package_name: package,
        f"{package_name}.const": const_module,
        "homeassistant": homeassistant,
        "homeassistant.components": components,
        "homeassistant.components.diagnostics": diagnostics_module,
        "homeassistant.config_entries": config_entries,
        "homeassistant.core": core,
    }
    with mock.patch.dict(sys.modules, stub_modules):
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
    return module


class DiagnosticsContractTest(unittest.IsolatedAsyncioTestCase):
    """Test diagnostics privacy in the dependency-free CI environment."""

    async def test_account_identity_and_tokens_are_redacted_in_ci(self) -> None:
        """Exercise the diagnostics function even when HA is not installed."""
        diagnostics_module = _load_diagnostics_with_homeassistant_stubs()

        diagnostics = await diagnostics_module.async_get_config_entry_diagnostics(
            None,
            FakeEntry(),
        )

        assert_private_values_are_redacted(self, diagnostics)


@unittest.skipUnless(HOME_ASSISTANT_AVAILABLE, "Home Assistant is not installed")
class HomeAssistantDiagnosticsTest(unittest.IsolatedAsyncioTestCase):
    """Test diagnostics against Home Assistant's real redaction helper."""

    async def test_account_identity_and_tokens_are_redacted(self) -> None:
        """Remove OAuth secrets and account identity throughout diagnostics."""
        diagnostics = await async_get_config_entry_diagnostics(None, FakeEntry())

        assert_private_values_are_redacted(self, diagnostics)


class FakeEntry:
    """Minimal config entry carrying private diagnostics values."""

    data = {
        "token": {"access_token": "secret-access"},
        "account_email": "person@example.com",
        "_meta": {"account_id": "account-secret"},
    }
    options = {"poll_interval": 300}

    def as_dict(self) -> dict[str, Any]:
        """Return the config-entry diagnostics shape."""
        return {
            "title": "person@example.com",
            "unique_id": "person@example.com",
            "data": self.data,
        }


def assert_private_values_are_redacted(
    test_case: unittest.TestCase,
    diagnostics: dict[str, Any],
) -> None:
    """Assert that no fixture secret or account identifier remains."""
    rendered = repr(diagnostics)

    for private_value in (
        "secret-access",
        "person@example.com",
        "account-secret",
    ):
        test_case.assertNotIn(private_value, rendered)
    test_case.assertEqual(diagnostics["options"], {"poll_interval": 300})


if __name__ == "__main__":
    unittest.main()

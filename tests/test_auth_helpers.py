"""Tests for OAuth helper functions."""

from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlparse

AUTH_HELPERS_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "hass_codex_usage"
    / "auth_helpers.py"
)
SPEC = importlib.util.spec_from_file_location(
    "hass_codex_usage_auth_helpers",
    AUTH_HELPERS_PATH,
)
auth_helpers = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(auth_helpers)


class AuthHelpersTest(unittest.TestCase):
    """Test OAuth helper functions."""

    def test_create_pkce_pair(self) -> None:
        """Create a verifier and matching S256 challenge."""
        verifier, challenge = auth_helpers.create_pkce_pair()
        expected = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).decode().rstrip("=")

        self.assertGreaterEqual(len(verifier), 43)
        self.assertEqual(challenge, expected)

    def test_build_authorization_url(self) -> None:
        """Build an authorization URL with Codex OAuth parameters."""
        url = auth_helpers.build_authorization_url("challenge-value", "state-value")
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(
            f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
            auth_helpers.OPENAI_AUTHORIZATION_URL,
        )
        self.assertEqual(query["response_type"], ["code"])
        self.assertEqual(query["client_id"], [auth_helpers.OPENAI_OAUTH_CLIENT_ID])
        self.assertEqual(query["redirect_uri"], [auth_helpers.OPENAI_REDIRECT_URI])
        self.assertEqual(query["scope"], [auth_helpers.OPENAI_OAUTH_SCOPE])
        self.assertEqual(query["code_challenge"], ["challenge-value"])
        self.assertEqual(query["code_challenge_method"], ["S256"])
        self.assertEqual(query["state"], ["state-value"])
        self.assertEqual(query["codex_cli_simplified_flow"], ["true"])

    def test_parse_authorization_response(self) -> None:
        """Parse direct codes and full redirect URLs."""
        self.assertEqual(
            auth_helpers.parse_authorization_response(" direct-code "),
            ("direct-code", None),
        )
        self.assertEqual(
            auth_helpers.parse_authorization_response(
                "http://localhost:1455/auth/callback?code=abc123&state=state123"
            ),
            ("abc123", "state123"),
        )

    def test_normalize_token(self) -> None:
        """Normalize token data while preserving refresh details."""
        id_token = self._id_token(
            {
                "email": "User@Example.COM",
                "sub": "account-123",
            }
        )
        token = auth_helpers.normalize_token(
            {
                "access_token": "access",
                "expires_in": 3600,
                "id_token": id_token,
            },
            previous_token={"refresh_token": "refresh"},
        )

        self.assertEqual(token["refresh_token"], "refresh")
        self.assertEqual(token["token_type"], "Bearer")
        self.assertEqual(token["account_email"], "user@example.com")
        self.assertEqual(token["account_id"], "account-123")
        self.assertGreater(token["expires_at"], 0)

    def test_normalize_token_ignores_invalid_expires_in(self) -> None:
        """Ignore invalid expires_in values instead of raising."""
        token = auth_helpers.normalize_token(
            {
                "access_token": "access",
                "expires_in": "not-a-number",
            }
        )

        self.assertNotIn("expires_at", token)
        self.assertEqual(token["token_type"], "Bearer")

    def test_token_needs_refresh(self) -> None:
        """Decide token refresh from stored expiry values."""
        self.assertFalse(
            auth_helpers.token_needs_refresh(
                {"expires_at": 2000},
                now=1000,
                margin_seconds=300,
            )
        )
        self.assertFalse(
            auth_helpers.token_needs_refresh(
                {"expires_at": "2000"},
                now=1000,
                margin_seconds=300,
            )
        )
        self.assertTrue(
            auth_helpers.token_needs_refresh(
                {"expires_at": 1200},
                now=1000,
                margin_seconds=300,
            )
        )
        self.assertTrue(
            auth_helpers.token_needs_refresh(
                {"expires_at": "not-a-number"},
                now=1000,
            )
        )
        self.assertTrue(
            auth_helpers.token_needs_refresh(
                {"expires_at": "nan"},
                now=1000,
            )
        )
        self.assertTrue(auth_helpers.token_needs_refresh({}))

    def test_reauth_unique_id(self) -> None:
        """Allow fallback unique IDs to improve to account email on reauth."""
        self.assertEqual(
            auth_helpers.reauth_unique_id(
                "hass_codex_usage",
                "user@example.com",
                "hass_codex_usage",
            ),
            ("user@example.com", False),
        )
        self.assertEqual(
            auth_helpers.reauth_unique_id(
                "old@example.com",
                "new@example.com",
                "hass_codex_usage",
            ),
            ("new@example.com", True),
        )
        self.assertEqual(
            auth_helpers.reauth_unique_id(
                "old@example.com",
                None,
                "hass_codex_usage",
            ),
            ("old@example.com", True),
        )
        self.assertEqual(
            auth_helpers.reauth_unique_id(
                None,
                None,
                "hass_codex_usage",
            ),
            ("hass_codex_usage", False),
        )

    def test_token_unique_id(self) -> None:
        """Prefer email unique IDs and use account IDs when email is absent."""
        self.assertEqual(
            auth_helpers.token_unique_id(
                {
                    "account_email": "User@Example.COM",
                    "account_id": "account-123",
                },
                "hass_codex_usage",
            ),
            "user@example.com",
        )
        self.assertEqual(
            auth_helpers.token_unique_id(
                {
                    "id_token": self._id_token({"sub": "account-123"}),
                },
                "hass_codex_usage",
            ),
            "account:account-123",
        )
        self.assertEqual(
            auth_helpers.token_unique_id({}, "hass_codex_usage"),
            "hass_codex_usage",
        )

    def test_reauth_unique_id_from_token(self) -> None:
        """Match reauth against any stable token identifier."""
        self.assertEqual(
            auth_helpers.reauth_unique_id_from_token(
                "account:account-123",
                {
                    "account_email": "user@example.com",
                    "account_id": "account-123",
                },
                "hass_codex_usage",
            ),
            ("account:account-123", True),
        )
        self.assertEqual(
            auth_helpers.reauth_unique_id_from_token(
                "old@example.com",
                {"account_email": "new@example.com"},
                "hass_codex_usage",
            ),
            ("new@example.com", True),
        )
        self.assertEqual(
            auth_helpers.reauth_unique_id_from_token(
                "hass_codex_usage",
                {"account_email": "user@example.com"},
                "hass_codex_usage",
            ),
            ("user@example.com", False),
        )

    def test_email_from_id_token_handles_invalid_values(self) -> None:
        """Ignore invalid ID token values."""
        self.assertIsNone(auth_helpers.email_from_id_token(None))
        self.assertIsNone(auth_helpers.email_from_id_token("not-a-token"))
        self.assertIsNone(auth_helpers.email_from_id_token(self._id_token({})))

    @staticmethod
    def _id_token(payload: dict[str, str]) -> str:
        """Create an unsigned test ID token."""
        encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
        return f"header.{encoded.rstrip('=')}.signature"


if __name__ == "__main__":
    unittest.main()

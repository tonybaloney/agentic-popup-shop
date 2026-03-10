"""
Unit tests for openid_auth module.

Tests _token_data_from_claims, AuthService.authenticate_user, and
AuthService.verify_token using mocked Keycloak responses — no running
Keycloak server is required.
"""

import os

# Set required env vars before any app imports
os.environ.setdefault("KEYCLOAK_SERVER_URL", "http://localhost:8080")
os.environ.setdefault("KEYCLOAK_REALM", "test-realm")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "test-client")
os.environ.setdefault("KEYCLOAK_CLIENT_SECRET", "test-secret")
os.environ.setdefault("SQLITE_DATABASE_PATH", ":memory:")

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from zava_shop_api.openid_auth import (
    AuthService,
    _token_data_from_claims,
)


# ---------------------------------------------------------------------------
# _token_data_from_claims
# ---------------------------------------------------------------------------

class TestTokenDataFromClaims:
    """Tests for the helper that builds TokenData from JWT claims."""

    def test_customer_claims(self):
        decoded = {
            "preferred_username": "stacey",
            "role": "customer",
            "store_id": 1,
            "customer_id": 4,
        }
        td = _token_data_from_claims(decoded, "tok-abc")
        assert td.username == "stacey"
        assert td.user_role == "customer"
        assert td.store_id == 1
        assert td.customer_id == 4
        assert td.access_token == "tok-abc"

    def test_admin_claims_no_store_or_customer(self):
        decoded = {
            "preferred_username": "admin",
            "role": "admin",
        }
        td = _token_data_from_claims(decoded, "tok-123")
        assert td.username == "admin"
        assert td.user_role == "admin"
        assert td.store_id is None
        assert td.customer_id is None

    def test_store_manager_with_string_store_id(self):
        """Keycloak user-attribute mappers may return strings for int fields."""
        decoded = {
            "preferred_username": "manager1",
            "role": "store_manager",
            "store_id": "1",
        }
        td = _token_data_from_claims(decoded, "tok-mgr")
        assert td.store_id == 1
        assert td.customer_id is None

    def test_missing_username_raises_401(self):
        decoded = {"role": "customer"}
        with pytest.raises(HTTPException) as exc_info:
            _token_data_from_claims(decoded, "tok")
        assert exc_info.value.status_code == 401
        assert "missing required claims" in exc_info.value.detail

    def test_missing_role_raises_401(self):
        decoded = {"preferred_username": "bob"}
        with pytest.raises(HTTPException) as exc_info:
            _token_data_from_claims(decoded, "tok")
        assert exc_info.value.status_code == 401

    def test_empty_claims_raises_401(self):
        with pytest.raises(HTTPException):
            _token_data_from_claims({}, "tok")


# ---------------------------------------------------------------------------
# AuthService.authenticate_user  (mocked keycloak_openid)
# ---------------------------------------------------------------------------

class TestAuthenticateUser:
    """Test authenticate_user with mocked keycloak_openid.token and decode_token."""

    _FAKE_JWT_CLAIMS = {
        "preferred_username": "stacey",
        "role": "customer",
        "store_id": 1,
        "customer_id": 4,
        "exp": 9999999999,
    }

    def test_successful_login(self):
        with (
            patch("zava_shop_api.openid_auth.keycloak_openid") as mock_kc,
        ):
            mock_kc.token.return_value = {"access_token": "jwt-xyz"}
            mock_kc.decode_token.return_value = self._FAKE_JWT_CLAIMS

            access_token, td = AuthService.authenticate_user("stacey", "stacey123")

            assert access_token == "jwt-xyz"
            assert td.username == "stacey"
            assert td.user_role == "customer"
            assert td.store_id == 1
            assert td.customer_id == 4

            # Verify decode_token was called with validate=False
            mock_kc.decode_token.assert_called_once_with("jwt-xyz", validate=False)

    def test_bad_password_raises_401(self):
        from keycloak.exceptions import KeycloakAuthenticationError

        with patch("zava_shop_api.openid_auth.keycloak_openid") as mock_kc:
            mock_kc.token.side_effect = KeycloakAuthenticationError()

            with pytest.raises(HTTPException) as exc_info:
                AuthService.authenticate_user("stacey", "wrong")
            assert exc_info.value.status_code == 401

    def test_empty_token_response_raises_401(self):
        with patch("zava_shop_api.openid_auth.keycloak_openid") as mock_kc:
            mock_kc.token.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                AuthService.authenticate_user("stacey", "stacey123")
            assert exc_info.value.status_code == 401

    def test_missing_claims_raise_401(self):
        """If Keycloak returns a JWT without the required claims, we get 401."""
        with patch("zava_shop_api.openid_auth.keycloak_openid") as mock_kc:
            mock_kc.token.return_value = {"access_token": "jwt-bad"}
            mock_kc.decode_token.return_value = {"sub": "abc"}  # no preferred_username / role

            with pytest.raises(HTTPException) as exc_info:
                AuthService.authenticate_user("stacey", "stacey123")
            assert exc_info.value.status_code == 401
            assert "missing required claims" in exc_info.value.detail


# ---------------------------------------------------------------------------
# AuthService.verify_token  (mocked keycloak_openid)
# ---------------------------------------------------------------------------

class TestVerifyToken:
    """Test verify_token with mocked keycloak_openid.decode_token."""

    _FAKE_JWT_CLAIMS = {
        "preferred_username": "manager1",
        "role": "store_manager",
        "store_id": 1,
        "exp": 9999999999,
    }

    def test_valid_token(self):
        with patch("zava_shop_api.openid_auth.keycloak_openid") as mock_kc:
            mock_kc.decode_token.return_value = self._FAKE_JWT_CLAIMS

            td = AuthService.verify_token("some-jwt")

            assert td.username == "manager1"
            assert td.user_role == "store_manager"
            assert td.store_id == 1
            assert td.customer_id is None
            assert td.access_token == "some-jwt"

            # Verify decode_token was called with validate=True (default)
            mock_kc.decode_token.assert_called_once_with("some-jwt")

    def test_expired_token_raises_401(self):
        with patch("zava_shop_api.openid_auth.keycloak_openid") as mock_kc:
            mock_kc.decode_token.side_effect = Exception("Token is expired")

            with pytest.raises(HTTPException) as exc_info:
                AuthService.verify_token("expired-jwt")
            assert exc_info.value.status_code == 401

    def test_tampered_token_raises_401(self):
        with patch("zava_shop_api.openid_auth.keycloak_openid") as mock_kc:
            mock_kc.decode_token.side_effect = Exception("Verification failed")

            with pytest.raises(HTTPException) as exc_info:
                AuthService.verify_token("bad-jwt")
            assert exc_info.value.status_code == 401

    def test_missing_claims_raise_401(self):
        with patch("zava_shop_api.openid_auth.keycloak_openid") as mock_kc:
            mock_kc.decode_token.return_value = {"sub": "no-role"}

            with pytest.raises(HTTPException) as exc_info:
                AuthService.verify_token("jwt-no-claims")
            assert exc_info.value.status_code == 401

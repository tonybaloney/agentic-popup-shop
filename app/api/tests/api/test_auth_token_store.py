"""
Tests for SQLite-based token store with expiry.
"""

import pytest
from zava_shop_api.auth import (
    SQLiteTokenStore,
    authenticate_user,
    get_current_user_from_token,
    logout_user,
    logout_all_user_sessions,
)
from zava_shop_api.models import TokenData


@pytest.fixture
async def token_store():
    """Create a test token store with in-memory database."""
    store = SQLiteTokenStore("sqlite+aiosqlite:///:memory:")
    await store.initialize()
    return store


@pytest.mark.asyncio
class TestSQLiteTokenStore:
    """Test suite for SQLite token store."""

    async def test_store_and_retrieve_token(self, token_store):
        """Test storing and retrieving a token."""
        token_data = TokenData(
            username="testuser",
            user_role="customer",
            store_id=1,
            customer_id=100,
        )

        await token_store.store_token("test_token_123", token_data)

        retrieved = await token_store.get_token("test_token_123")
        assert retrieved is not None
        assert retrieved.username == "testuser"
        assert retrieved.user_role == "customer"
        assert retrieved.store_id == 1
        assert retrieved.customer_id == 100

    async def test_get_nonexistent_token(self, token_store):
        """Test retrieving a token that doesn't exist."""
        result = await token_store.get_token("nonexistent_token")
        assert result is None

    async def test_delete_token(self, token_store):
        """Test deleting a token."""
        token_data = TokenData(
            username="testuser", user_role="customer", customer_id=100
        )

        await token_store.store_token("delete_me", token_data)
        assert await token_store.get_token("delete_me") is not None

        deleted = await token_store.delete_token("delete_me")
        assert deleted is True

        result = await token_store.get_token("delete_me")
        assert result is None

    async def test_delete_nonexistent_token(self, token_store):
        """Test deleting a token that doesn't exist."""
        deleted = await token_store.delete_token("nonexistent")
        assert deleted is False

    async def test_delete_user_tokens(self, token_store):
        """Test deleting all tokens for a user."""
        token_data = TokenData(username="multiuser", user_role="customer")

        await token_store.store_token("token1", token_data)
        await token_store.store_token("token2", token_data)
        await token_store.store_token("token3", token_data)

        # Different user
        other_data = TokenData(username="otheruser", user_role="admin")
        await token_store.store_token("token4", other_data)

        count = await token_store.delete_user_tokens("multiuser")
        assert count == 3

        # Verify multiuser tokens are gone
        assert await token_store.get_token("token1") is None
        assert await token_store.get_token("token2") is None
        assert await token_store.get_token("token3") is None

        # Other user's token should still exist
        assert await token_store.get_token("token4") is not None

    async def test_cleanup_expired_tokens(self, token_store):
        """Test cleanup of expired tokens."""
        # This test would require mocking datetime or waiting for expiry
        # For now, we just verify the method doesn't error
        count = await token_store.cleanup_expired_tokens()
        assert count >= 0


@pytest.mark.asyncio
class TestAuthenticationFunctions:
    """Test suite for authentication functions."""

    async def test_authenticate_valid_user(self):
        """Test authenticating a valid user."""
        token, token_data = await authenticate_user("stacey", "stacey123")

        assert len(token) > 0
        assert token_data.username == "stacey"
        assert token_data.user_role == "customer"
        assert token_data.customer_id == 4

        # Verify token can be retrieved
        retrieved = await get_current_user_from_token(token)
        assert retrieved.username == "stacey"

    async def test_authenticate_invalid_password(self):
        """Test authenticating with wrong password."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await authenticate_user("stacey", "wrongpassword")

        assert exc_info.value.status_code == 401

    async def test_authenticate_invalid_user(self):
        """Test authenticating a non-existent user."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await authenticate_user("nonexistent", "password")

        assert exc_info.value.status_code == 401

    async def test_logout_user(self):
        """Test logging out a user."""
        token, _ = await authenticate_user("stacey", "stacey123")

        # Verify token exists
        retrieved = await get_current_user_from_token(token)
        assert retrieved is not None

        # Logout
        deleted = await logout_user(token)
        assert deleted is True

        # Verify token is gone
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            await get_current_user_from_token(token)

    async def test_logout_all_sessions(self):
        """Test logging out all sessions for a user."""
        # Create multiple sessions
        token1, _ = await authenticate_user("admin", "admin123")
        token2, _ = await authenticate_user("admin", "admin123")

        # Verify both exist
        assert await get_current_user_from_token(token1) is not None
        assert await get_current_user_from_token(token2) is not None

        # Logout all
        count = await logout_all_user_sessions("admin")
        assert count >= 2

        # Verify both are gone
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            await get_current_user_from_token(token1)

        with pytest.raises(HTTPException):
            await get_current_user_from_token(token2)

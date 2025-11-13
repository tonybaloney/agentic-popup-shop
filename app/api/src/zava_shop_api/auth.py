import os
from fastapi import HTTPException, Header
import secrets
import logging
from typing import Optional
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
)
from sqlalchemy import Column, String, Integer, DateTime, select, delete
from sqlalchemy.orm import declarative_base

from zava_shop_api.models import TokenData

logger = logging.getLogger(__name__)

Base = declarative_base()


class SessionToken(Base):
    """SQLAlchemy model for session tokens"""

    __tablename__ = "session_tokens"

    token = Column(String, primary_key=True, index=True)
    username = Column(String, nullable=False)
    user_role = Column(String, nullable=False)
    store_id = Column(Integer, nullable=True)
    customer_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


ABS_DB_PATH = "sqlite+aiosqlite:////workspace/app/data/auth.db"
REL_DB_PATH = "sqlite+aiosqlite:///../../data/auth.db"

import pathlib

# Use absolute path if running in container (/workspace exists), else relative path
if pathlib.Path("/workspace").exists():
    DEFAULT_SQLITE_URL = ABS_DB_PATH
else:
    DEFAULT_SQLITE_URL = REL_DB_PATH

class SQLiteTokenStore:
    """Provides SQLite database access for token storage with automatic expiry."""

    # Token expiry duration: 48 hours
    TOKEN_EXPIRY_HOURS = 48

    def __init__(self, sqlite_url: Optional[str] = None) -> None:
        # Use the same database as the retail data
        self.sqlite_url = (
            sqlite_url or DEFAULT_SQLITE_URL
        )
        self.engine: Optional[AsyncEngine] = None
        self.async_session_factory: Optional[async_sessionmaker] = None

    async def initialize(self) -> None:
        """Initialize database engine and create tables if they don't exist."""
        if self.engine is None:
            self.engine = create_async_engine(
                self.sqlite_url,
                echo=False,
                connect_args={"check_same_thread": False},
            )
            self.async_session_factory = async_sessionmaker(
                self.engine, class_=AsyncSession, expire_on_commit=False
            )

            # Create tables if they don't exist
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            logger.info("SQLiteTokenStore initialized with database: %s", self.sqlite_url)

    async def cleanup_expired_tokens(self) -> int:
        """Remove all expired tokens from the database. Returns count of deleted tokens."""
        if not self.async_session_factory:
            await self.initialize()

        async with self.async_session_factory() as session:
            stmt = delete(SessionToken).where(SessionToken.expires_at < datetime.utcnow())
            result = await session.execute(stmt)
            await session.commit()
            deleted_count = result.rowcount
            if deleted_count > 0:
                logger.info("Cleaned up %d expired tokens", deleted_count)
            return deleted_count

    async def store_token(
        self, token: str, token_data: TokenData
    ) -> None:
        """Store a new session token in the database."""
        if not self.async_session_factory:
            await self.initialize()

        # Clean up expired tokens periodically
        await self.cleanup_expired_tokens()

        expires_at = datetime.utcnow() + timedelta(hours=self.TOKEN_EXPIRY_HOURS)

        session_token = SessionToken(
            token=token,
            username=token_data.username,
            user_role=token_data.user_role,
            store_id=token_data.store_id,
            customer_id=token_data.customer_id,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
        )

        async with self.async_session_factory() as session:
            session.add(session_token)
            await session.commit()
            logger.info(
                "Stored token for user '%s' (expires at %s)",
                token_data.username,
                expires_at.isoformat(),
            )

    async def get_token(self, token: str) -> Optional[TokenData]:
        """Retrieve token data from database. Returns None if token doesn't exist or is expired."""
        if not self.async_session_factory:
            await self.initialize()

        async with self.async_session_factory() as session:
            stmt = select(SessionToken).where(SessionToken.token == token)
            result = await session.execute(stmt)
            session_token = result.scalar_one_or_none()

            if session_token is None:
                return None

            # Check if token has expired
            if session_token.expires_at < datetime.utcnow():
                logger.info("Token expired for user '%s'", session_token.username)
                # Delete the expired token
                await session.delete(session_token)
                await session.commit()
                return None

            return TokenData(
                username=session_token.username,
                user_role=session_token.user_role,
                store_id=session_token.store_id,
                customer_id=session_token.customer_id,
            )

    async def delete_token(self, token: str) -> bool:
        """Delete a token from the database. Returns True if token was found and deleted."""
        if not self.async_session_factory:
            await self.initialize()

        async with self.async_session_factory() as session:
            stmt = delete(SessionToken).where(SessionToken.token == token)
            result = await session.execute(stmt)
            await session.commit()
            deleted = result.rowcount > 0
            if deleted:
                logger.info("Deleted token from store")
            return deleted

    async def delete_user_tokens(self, username: str) -> int:
        """Delete all tokens for a specific user. Returns count of deleted tokens."""
        if not self.async_session_factory:
            await self.initialize()

        async with self.async_session_factory() as session:
            stmt = delete(SessionToken).where(SessionToken.username == username)
            result = await session.execute(stmt)
            await session.commit()
            deleted_count = result.rowcount
            if deleted_count > 0:
                logger.info("Deleted %d tokens for user '%s'", deleted_count, username)
            return deleted_count


# Global token store instance
token_store = SQLiteTokenStore()

# TODO: Switch auth models based on ENV
logger = logging.getLogger(__name__)
class UserAuthModel(dict):  # this should be internal to this module
    password: str
    role: str  # 'admin', 'store_manager', 'customer'
    store_id: int | None = None  # For store managers
    customer_id: int | None = None  # For customers

# Static user database (in production, this would be in a database with hashed passwords)
USERS: dict[str, UserAuthModel] = {
    "admin": UserAuthModel(
        password=os.environ.get("DEMO_PASSWORD", "admin123"),
        role="admin",
        store_id=None
    ),
    "manager1": UserAuthModel(
        password=os.environ.get("DEMO_PASSWORD", "manager123"),
        role="store_manager",
        store_id=1  # NYC Times Square
    ),
    "manager2": UserAuthModel(
        password=os.environ.get("DEMO_PASSWORD", "manager123"),
        role="store_manager",
        store_id=2  # SF Union Square
    ),
    "stacey": UserAuthModel(
        password=os.environ.get("DEMO_PASSWORD", "stacey123"),
        role="customer",
        store_id=1,
        customer_id=4
    ),
    "marketing": UserAuthModel(
        password=os.environ.get("DEMO_PASSWORD", "marketing123"),
        role="marketing",
        store_id=None
    ),
}


# Authentication helper functions
def generate_token() -> str:
    """Generate a random secure token"""
    return secrets.token_urlsafe(32)


async def get_current_user(authorization: str = Header(...)) -> TokenData:
    """
    Dependency to get current user from bearer token.
    Raises HTTPException if token is invalid or missing.
    """
    if not authorization.startswith("Bearer "):
        logger.warning("Missing or invalid Authorization header (not bearer)")
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.replace("Bearer ", "")

    token_data = await token_store.get_token(token)
    if token_data is None:
        logger.warning("Invalid or expired token")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_data


async def get_current_user_from_token(token: str) -> TokenData:
    """Get user data from a token string directly."""
    token_data = await token_store.get_token(token)
    if token_data is None:
        logger.warning("Invalid or expired token for user retrieval")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_data

async def authenticate_user(username: str, password: str) -> tuple[str, TokenData]:
    """
    Authenticate user and return TokenData if successful.
    Raises HTTPException if authentication fails.
    """
    user = USERS.get(username)
    if not user or user["password"] != password:
        logger.warning(
            "Authentication failed for user: %s (bad password or not a user)",
            username,
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = TokenData(
        username=username,
        user_role=user["role"],
        store_id=user.get("store_id"),
        customer_id=user.get("customer_id"),
    )

    # Generate and store token in SQLite with 48-hour expiry
    token = generate_token()
    await token_store.store_token(token, token_data)
    logger.info("User '%s' authenticated successfully", username)

    return token, token_data


async def logout_user(token: str) -> bool:
    """
    Logout user by deleting their token.
    Returns True if token was found and deleted.
    """
    deleted = await token_store.delete_token(token)
    if deleted:
        logger.info("User logged out successfully")
    return deleted


async def logout_all_user_sessions(username: str) -> int:
    """
    Logout all sessions for a specific user.
    Returns the count of deleted tokens.
    """
    count = await token_store.delete_user_tokens(username)
    logger.info("Logged out %d sessions for user '%s'", count, username)
    return count


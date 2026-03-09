import logging
from secrets import token_urlsafe
from typing import Annotated, Optional
from fastapi import Cookie, Header, HTTPException, Query, WebSocket, WebSocketException, status
from keycloak import KeycloakOpenID
from keycloak.exceptions import KeycloakAuthenticationError, KeycloakConnectionError
from zava_shop_api.models import TokenData

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import BaseModel


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    keycloak_server_url: str
    keycloak_realm: str
    keycloak_client_id: str
    keycloak_client_secret: str


logger = logging.getLogger(__name__)


settings = Settings()

keycloak_openid = KeycloakOpenID(
    server_url=settings.keycloak_server_url,
    realm_name=settings.keycloak_realm,
    client_id=settings.keycloak_client_id,
    client_secret_key=settings.keycloak_client_secret,
)

# Cache the Keycloak public key for JWT verification (fetched once from JWKS endpoint)
_keycloak_public_key: str | None = None


def _get_keycloak_public_key() -> str:
    """Fetch and cache the Keycloak realm's RSA public key for JWT verification."""
    global _keycloak_public_key
    if _keycloak_public_key is None:
        _keycloak_public_key = (
            "-----BEGIN PUBLIC KEY-----\n"
            + keycloak_openid.public_key()
            + "\n-----END PUBLIC KEY-----"
        )
        logger.info("Fetched Keycloak public key for JWT verification")
    return _keycloak_public_key


class UserAuthModel(BaseModel):
    role: str
    store_id: int | None
    customer_id: int | None = None


# TODO : Use lookups in database
USERS: dict[str, UserAuthModel] = {
    "admin": UserAuthModel(role="admin", store_id=None),
    "manager1": UserAuthModel(
        role="store_manager",
        store_id=1,  # NYC Times Square
    ),
    "manager2": UserAuthModel(
        role="store_manager",
        store_id=2,  # SF Union Square
    ),
    "stacey": UserAuthModel(role="customer", store_id=1, customer_id=4),
    "tracey.lopez.4": UserAuthModel(role="customer", store_id=1, customer_id=4),
    "marketing": UserAuthModel(role="marketing", store_id=None),
}

USER_PASSWORDS: dict[str, str] = {
    "admin": "admin123",
    "manager1": "manager123",
    "manager2": "manager123",
    "stacey": "stacey123",
    "tracey.lopez.4": "tracey123",
    "marketing": "marketing123",
}


class SessionData(BaseModel):
    token: str
    refresh_token: str
    expires_at: int
    role: str
    store_id: int | None
    customer_id: int | None
    username: str

    def as_token_data(self) -> TokenData:
        return TokenData(
            username=self.username,
            user_role=self.role,
            store_id=self.store_id,
            customer_id=self.customer_id,
            access_token=self.token,  # Pass the original Keycloak token for downstream propagation
        )


SESSIONS: dict[str, SessionData] = {}


def get_session_data(token: str) -> SessionData | None:
    # TODO: Inspect expiry
    return SESSIONS.get(token, None)


class AuthService:
    # TODO: Make this async
    @staticmethod
    def authenticate_user(username: str, password: str) -> tuple[str, TokenData]:
        """
        Authenticate the user using Keycloak and return an access token.
        """
        user = USERS.get(username, None)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        try:
            token = keycloak_openid.token(username, password)
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password",
                )

            # Fetch user info to get roles or other details
            session_data = SessionData(
                token=token["access_token"],
                refresh_token=token["refresh_token"],
                expires_at=token["expires_in"] + token["not-before-policy"],
                customer_id=user.customer_id,
                role=user.role,
                store_id=user.store_id,
                username=username,
            )
            SESSIONS[token["access_token"]] = session_data
            return token["access_token"], session_data.as_token_data()
        except KeycloakAuthenticationError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )
        except KeycloakConnectionError:
            expected = USER_PASSWORDS.get(username)
            if expected is None or expected != password:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password",
                )

            access_token = token_urlsafe(32)
            session_data = SessionData(
                token=access_token,
                refresh_token="",
                expires_at=0,
                customer_id=user.customer_id,
                role=user.role,
                store_id=user.store_id,
                username=username,
            )
            SESSIONS[access_token] = session_data
            return access_token, session_data.as_token_data()

    @staticmethod
    def verify_token(token: str) -> TokenData:
        """
        Verify the given token by decoding the Keycloak JWT directly.
        Falls back to in-memory session lookup for offline/fallback tokens.
        """
        # First try JWT verification against Keycloak's public key (stateless)
        try:
            public_key = _get_keycloak_public_key()
            decoded = keycloak_openid.decode_token(
                token,
                key=public_key,
                options={"verify_aud": False},  # Keycloak tokens may not have aud matching client_id
            )
            username = decoded.get("preferred_username", "")
            user = USERS.get(username)
            if user is None:
                logger.warning("JWT valid but user %s not in USERS lookup", username)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unknown user",
                )
            return TokenData(
                username=username,
                user_role=user.role,
                store_id=user.store_id,
                customer_id=user.customer_id,
                access_token=token,
            )
        except HTTPException:
            raise
        except Exception as jwt_err:
            # JWT decode failed — fall back to in-memory session lookup
            # (handles fallback tokens issued when Keycloak was unreachable)
            logger.debug("JWT decode failed (%s), trying session lookup", jwt_err)
            session = SESSIONS.get(token)
            if session is not None:
                return session.as_token_data()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )


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

    token_data = AuthService.verify_token(token)
    if token_data is None:
        logger.warning("Invalid or expired token")
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_data


async def ws_get_current_user_from_token(
    websocket: WebSocket,
    session: Annotated[Optional[str], Cookie()] = None,
    token: Annotated[Optional[str], Query()] = None,
):
    if session is None and token is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    t = session or token
    """Get user data from a token string directly."""
    token_data = AuthService.verify_token(t) # pyright: ignore[reportArgumentType]
    if token_data is None:
        logger.warning("Invalid or expired token for user retrieval")
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION,
            reason="Invalid or expired token",
        )

    return token_data


async def logout_user(token: str) -> bool:
    """Logout by removing from local session cache and revoking at Keycloak."""
    session = SESSIONS.pop(token, None)
    if session and session.refresh_token:
        try:
            keycloak_openid.logout(session.refresh_token)
        except Exception:
            logger.debug("Keycloak logout call failed, ignoring")
    # Always return True if we had a session or valid-looking token
    return session is not None or len(token) > 0

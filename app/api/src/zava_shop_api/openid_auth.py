import logging
from typing import Annotated, Optional
from fastapi import Cookie, Header, HTTPException, Query, WebSocket, WebSocketException, status
from keycloak import KeycloakOpenID
from keycloak.exceptions import KeycloakAuthenticationError
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


class AuthService:
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

            token_data = TokenData(
                username=username,
                user_role=user.role,
                store_id=user.store_id,
                customer_id=user.customer_id,
                access_token=token["access_token"],
            )
            return token["access_token"], token_data
        except KeycloakAuthenticationError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

    @staticmethod
    def verify_token(token: str) -> TokenData:
        """
        Verify the given token by decoding the Keycloak JWT directly.
        Fully stateless — no server-side session storage required.
        """
        try:
            public_key = _get_keycloak_public_key()
            decoded = keycloak_openid.decode_token(
                token,
                key=public_key,
                options={"verify_aud": False},
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
            logger.debug("JWT decode failed: %s", jwt_err)
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
    """Logout is client-side only — JWT tokens expire naturally.
    The frontend clears sessionStorage; no server-side state to invalidate."""
    return True

import logging
from typing import Annotated, Optional
from fastapi import Cookie, Header, HTTPException, Query, WebSocket, WebSocketException, status
from keycloak import KeycloakOpenID
from keycloak.exceptions import KeycloakAuthenticationError
from zava_shop_api.models import TokenData

from pydantic_settings import BaseSettings, SettingsConfigDict


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


def _token_data_from_claims(decoded: dict, access_token: str) -> TokenData:
    """Build TokenData from JWT claims.

    The Keycloak 'zava:profile' client scope maps user attributes
    (role, store_id, customer_id) into the access-token claims.
    """
    username = decoded.get("preferred_username", "")
    role = decoded.get("role", "")
    store_id_raw = decoded.get("store_id")
    customer_id_raw = decoded.get("customer_id")

    if not username or not role:
        logger.warning("JWT missing required claims (preferred_username=%s, role=%s)", username, role)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing required claims",
        )

    return TokenData(
        username=username,
        user_role=role,
        store_id=int(store_id_raw) if store_id_raw is not None else None,
        customer_id=int(customer_id_raw) if customer_id_raw is not None else None,
        access_token=access_token,
    )


class AuthService:
    @staticmethod
    def authenticate_user(username: str, password: str) -> tuple[str, TokenData]:
        """
        Authenticate the user using Keycloak and return an access token.

        Role, store_id, and customer_id are read from JWT claims
        (populated by Keycloak user attributes via the zava:profile scope).
        """
        try:
            token = keycloak_openid.token(username, password)
            if not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password",
                )

            access_token = token["access_token"]
            # Decode without verification — we just minted this token
            public_key = _get_keycloak_public_key()
            decoded = keycloak_openid.decode_token(
                access_token,
                key=public_key,
                options={"verify_aud": False},
            )
            token_data = _token_data_from_claims(decoded, access_token)
            return access_token, token_data
        except HTTPException:
            raise
        except KeycloakAuthenticationError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

    @staticmethod
    def verify_token(token: str) -> TokenData:
        """
        Verify the given token by decoding the Keycloak JWT directly.
        Fully stateless — role, store_id, customer_id come from JWT claims.
        """
        try:
            public_key = _get_keycloak_public_key()
            decoded = keycloak_openid.decode_token(
                token,
                key=public_key,
                options={"verify_aud": False},
            )
            return _token_data_from_claims(decoded, token)
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

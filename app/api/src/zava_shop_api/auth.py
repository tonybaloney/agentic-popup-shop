
# Token storage (in-memory for simplicity - in production use Redis or database)
# Maps token -> TokenData
from fastapi import HTTPException, Header
import secrets

from zava_shop_api.models import TokenData

active_tokens: dict[str, TokenData] = {}

# TODO: Switch auth models based on ENV

class UserAuthModel(dict):  # this should be internal to this module
    password: str
    role: str  # 'admin', 'store_manager', 'customer'
    store_id: int | None = None  # For store managers
    customer_id: int | None = None  # For customers

# Static user database (in production, this would be in a database with hashed passwords)
USERS: dict[str, UserAuthModel] = {
    "admin": UserAuthModel(
        password="admin123",
        role="admin",
        store_id=None
    ),
    "manager1": UserAuthModel(
        password="manager123",
        role="store_manager",
        store_id=1  # NYC Times Square
    ),
    "manager2": UserAuthModel(
        password="manager123",
        role="store_manager",
        store_id=2  # SF Union Square
    ),
    "tracey.lopez.4": UserAuthModel(
        password="tracey123",
        role="customer",
        store_id=1,
        customer_id=4
    )
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
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.replace("Bearer ", "")
    
    if token not in active_tokens:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return active_tokens[token]


async def get_current_user_from_token(token: str) -> TokenData:
    if token not in active_tokens:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return active_tokens[token]

async def authenticate_user(username: str, password: str) -> tuple[str, TokenData]:
    """
    Authenticate user and return TokenData if successful.
    Raises HTTPException if authentication fails
    """
    user = USERS.get(username)
    if not user or user["password"] != password:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = TokenData(
        username=username,
        user_role=user["role"],
        store_id=user.get("store_id"),
        customer_id=user.get("customer_id")
    )

    # Generate and store token
    token = generate_token()
    active_tokens[token] = token_data

    return token, token_data
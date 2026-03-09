#!/usr/bin/env python3
"""
FastAPI Backend for Popup Store
Provides REST API endpoints for the frontend application.
"""

from opentelemetry.instrumentation.auto_instrumentation import initialize
initialize()

import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
# Initialize in startup event
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache


from zava_shop_api.routers.chatkit import router as chatkit_router
from zava_shop_api.routers.management import router as management_router
from zava_shop_api.routers.products import router as products_router
from zava_shop_api.routers.returns import router as returns_router
from zava_shop_api.routers.users import router as users_router

from zava_shop_shared.config import Config

# SQLAlchemy imports for SQLite
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from zava_shop_shared.models.sqlite.stores import Store as StoreModel
from zava_shop_shared.models.sqlite.inventory import Inventory as InventoryModel
from zava_shop_shared.models.sqlite.products import Product as ProductModel
from zava_shop_shared.models.sqlite.categories import Category as CategoryModel
from zava_shop_shared.models.sqlite.customers import Customer as CustomerModel
from .models import (
    Store, StoreList, Category, CategoryList,
    LoginRequest, LoginResponse,
)

from .openid_auth import (
    AuthService,
    logout_user,
)
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
config = Config()


async def get_store_name(store_id: int, request: Request) -> Optional[str]:
    """Get store name by ID"""
    try:
        async with request.app.state.session_factory() as session:
            stmt = select(StoreModel.store_name).where(StoreModel.store_id == store_id)
            result = await session.execute(stmt)
            store_name = result.scalar_one_or_none()
            return store_name
    except Exception:
        return None


async def get_user_name(user_id: int, request: Request) -> Optional[str]:
    """Get user name by ID"""
    try:
        async with request.app.state.session_factory() as session:
            stmt = select(CustomerModel.first_name, CustomerModel.last_name).where(CustomerModel.customer_id == user_id)
            result = await session.execute(stmt)
            row = result.first()
            if row:
                return f"{row.first_name} {row.last_name}"
            return None
    except Exception:
        return None


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown events"""
    # Startup
    logger.info("Starting API Server...")

    # Initialize SQLAlchemy async engine for SQLite
    try:
        sqlite_url = config.sqlite_database_url
        logger.info(f"Connecting to SQLite database at {sqlite_url}...")
        sqlalchemy_engine = create_async_engine(
            sqlite_url,
            connect_args={"timeout": 30, "check_same_thread": False},
            pool_pre_ping=True,
            echo=False,
        )
        SQLAlchemyInstrumentor().instrument(
            engine=sqlalchemy_engine.sync_engine,
            enable_commenter=True, commenter_options={}  # TODO : disable this in prod
        )
        # Create async session factory
        async_session_factory = async_sessionmaker(
            sqlalchemy_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        logger.info(f"SQLAlchemy async engine created: {sqlite_url}")

    except Exception as e:
        logger.error(f"Failed to initialize SQLAlchemy: {e}")
        raise

    # Initialize cache
    backend = InMemoryBackend()
    FastAPICache.init(backend=backend)

    # Store on app.state so routers can access them
    app.state.engine = sqlalchemy_engine
    app.state.session_factory = async_session_factory

    yield

    # Shutdown
    logger.info("Shutting down API Server...")

    # Dispose SQLAlchemy engine
    if sqlalchemy_engine:
        await sqlalchemy_engine.dispose()
        logger.info("SQLAlchemy async engine disposed")


# Create FastAPI app
app = FastAPI(
    title="Popup Store API",
    description="REST API for Popup merchandise store",
    version="1.0.0",
    lifespan=lifespan
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite default
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chatkit_router)
app.include_router(management_router)
app.include_router(products_router)
app.include_router(returns_router)
app.include_router(users_router)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy"
    }


# Authentication endpoint
@app.post("/api/login", response_model=LoginResponse)
async def login(credentials: LoginRequest, request: Request) -> LoginResponse:
    """
    Login endpoint to authenticate users and receive bearer token.

    Supports two user roles:
    - admin: Can see all stores
    - store_manager: Can only see their assigned store
    """
    token, user = AuthService.authenticate_user(credentials.username, credentials.password)

    # Get store name if store manager
    store_name = None
    if user.store_id:
        store_name = await get_store_name(user.store_id, request)
    if user.customer_id:
        name = await get_user_name(user.customer_id, request)
    else:
        name = None

    logger.info(f"User {credentials.username} ({user.user_role}) logged in")

    return LoginResponse(
        access_token=token,
        token_type="bearer",  # noqa: S106
        user_role=user.user_role,
        store_id=user.store_id,
        store_name=store_name,
        name=name
    )

@app.post("/api/logout")
async def logout(authorization: str = Header(None)):
    """Logout the current user from this session."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")
    success = await logout_user(token)

    if success:
        return {"message": "Successfully logged out"}
    else:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

# Stores endpoint
@app.get("/api/stores", response_model=StoreList)
@cache(expire=600)
async def get_stores(request: Request) -> StoreList:
    """
    Get all store locations with inventory counts and details.
    Returns comprehensive store information for the stores page.
    """
    try:
        async with request.app.state.session_factory() as session:
            # Build SQLAlchemy query with aggregations
            stmt = (
                select(
                    StoreModel.store_id,
                    StoreModel.store_name,
                    StoreModel.is_online,
                    func.count(func.distinct(InventoryModel.product_id)).label(
                        "product_count"
                    ),
                    func.sum(InventoryModel.stock_level).label("total_stock"),
                    func.sum(
                        InventoryModel.stock_level * ProductModel.cost
                    ).label("inventory_cost_value"),
                    func.sum(
                        InventoryModel.stock_level * ProductModel.base_price
                    ).label("inventory_retail_value"),
                )
                .select_from(StoreModel)
                .outerjoin(
                    InventoryModel,
                    StoreModel.store_id == InventoryModel.store_id
                )
                .outerjoin(
                    ProductModel,
                    InventoryModel.product_id == ProductModel.product_id
                )
                .group_by(
                    StoreModel.store_id,
                    StoreModel.store_name,
                    StoreModel.is_online
                )
                .order_by(StoreModel.is_online.asc(), StoreModel.store_name)
            )

            result = await session.execute(stmt)
            rows = result.all()

            stores: list[Store] = []
            for row in rows:
                store_name = row.store_name

                # Extract location key for images
                if row.is_online:
                    location_key = "online"
                    location = "Online Warehouse, Seattle, WA"
                else:
                    # Extract location from "GitHub Popup Location" format
                    parts = store_name.split('Popup ')
                    if len(parts) > 1:
                        location_name = parts[1]
                        location_key = location_name.lower().replace(' ', '_')
                        # Format address from location name
                        location = location_name
                    else:
                        location_key = store_name.lower().replace(' ', '_')
                        location = "Washington State"

                stores.append(Store(
                    id=row.store_id,
                    name=store_name,
                    location=location,
                    is_online=row.is_online,
                    location_key=location_key,
                    products=int(row.product_count or 0),
                    total_stock=int(row.total_stock or 0),
                    inventory_value=round(
                        float(row.inventory_retail_value or 0), 2
                    ),
                    status="Online" if row.is_online else "Open",
                    hours=(
                        "24/7 Online" if row.is_online
                        else "Mon-Sun: 10am-7pm"
                    )
                ))

            logger.info(f"Retrieved {len(stores)} stores")

            return StoreList(stores=stores, total=len(stores))

    except Exception as e:
        logger.error(f"Error fetching stores: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch stores: {str(e)}"
        )


# Categories endpoint
@app.get("/api/categories", response_model=CategoryList)
@cache(expire=3600)
async def get_categories(request: Request) -> CategoryList:
    """
    Get all product categories.
    Returns a list of all available categories in the system.
    """
    try:
        async with request.app.state.session_factory() as session:
            # Build SQLAlchemy query for categories
            stmt = (
                select(
                    CategoryModel.category_id,
                    CategoryModel.category_name
                )
                .order_by(CategoryModel.category_name)
            )

            result = await session.execute(stmt)
            rows = result.all()

            categories: list[Category] = []
            for row in rows:
                categories.append(Category(
                    id=row.category_id,
                    name=row.category_name
                ))

            logger.info(f"Retrieved {len(categories)} categories")

            return CategoryList(categories=categories, total=len(categories))

    except Exception as e:
        logger.error(f"Error fetching categories: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch categories: {str(e)}"
        )


# Root endpoint
@app.get("/")
@cache(expire=600)
async def root():
    """Root endpoint"""
    return {
        "service": "Popup Store API",
        "version": "1.0.0",
        "status": "running"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8091,
        log_level="info"
    )

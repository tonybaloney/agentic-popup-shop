#!/usr/bin/env python3
"""
FastAPI Backend for Popup Store
Provides REST API endpoints for the frontend application.
"""
import os

if os.environ.get("ENABLE_VSCODE_TRACING", "false").lower() == "true":
    from agent_framework.observability import setup_observability
    setup_observability(vs_code_extension_port=4319)

from opentelemetry.instrumentation.auto_instrumentation import initialize
initialize()

import logging
from contextlib import asynccontextmanager
from typing import Optional

from agent_framework import (ChatMessage,
                             ExecutorInvokedEvent,
                             ExecutorCompletedEvent,
                             ExecutorFailedEvent,
                             WorkflowOutputEvent,
                             WorkflowStartedEvent)
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
# Initialize in startup event
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from fastapi_cache.decorator import cache

from pydantic import BaseModel
import json
from datetime import datetime, timezone

from zava_shop_api.chatkit_router import router as chatkit_router
from zava_shop_api.routers.marketing import router as marketing_router, ws_router as marketing_ws_router

from zava_shop_shared.config import Config
from zava_shop_agents.stock import workflow as stock_workflow
from zava_shop_agents.admin_insights import admin_workflow as admin_insights_workflow
from zava_shop_agents.insights import workflow as insights_workflow

# SQLAlchemy imports for SQLite
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from zava_shop_shared.models.sqlite.stores import Store as StoreModel
from zava_shop_shared.models.sqlite.inventory import Inventory as InventoryModel
from zava_shop_shared.models.sqlite.products import Product as ProductModel
from zava_shop_shared.models.sqlite.categories import Category as CategoryModel
from zava_shop_shared.models.sqlite.product_types import ProductType as ProductTypeModel
from zava_shop_shared.models.sqlite.suppliers import Supplier as SupplierModel
from zava_shop_shared.models.sqlite.customers import Customer as CustomerModel
from .models import (
    Product, ProductList, Store, StoreList, Category, CategoryList,
    TopCategory, TopCategoryList, Supplier, SupplierList,
    InventoryItem, InventorySummary, InventoryResponse,
    ManagementProduct, ProductPagination, ManagementProductResponse,
    LoginRequest, LoginResponse, TokenData,
    WeeklyInsights, Insight, CacheInvalidationResponse, CacheInfoResponse, 
    OrderListResponse, CustomerProfile,
)
from zava_shop_agents.insights_cache import get_cache
from .customers import get_customer_orders
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from zava_shop_api.auth import (
    authenticate_user,
    get_current_user,
    get_current_user_from_token,
    logout_user,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
config = Config()

# Database connections
sqlalchemy_engine: Optional[AsyncEngine] = None
async_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


async def get_store_name(store_id: int) -> Optional[str]:
    """Get store name by ID"""
    try:
        async with get_db_session() as session:
            stmt = select(StoreModel.store_name).where(StoreModel.store_id == store_id)
            result = await session.execute(stmt)
            store_name = result.scalar_one_or_none()
            return store_name
    except Exception:
        return None


async def get_user_name(user_id: int) -> Optional[str]:
    """Get user name by ID"""
    try:
        async with get_db_session() as session:
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
    global sqlalchemy_engine, async_session_factory

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

    # Initialize token store
    try:
        from zava_shop_api.auth import token_store
        await token_store.initialize()
        logger.info("Token store initialized")
    except Exception as e:
        logger.error(f"Failed to initialize token store: {e}")
        raise

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


# Helper function to get SQLAlchemy session
def get_db_session() -> AsyncSession:
    """
    Get a new SQLAlchemy async session.

    Returns:
        AsyncSession: A new async database session

    Raises:
        RuntimeError: If the session factory is not initialized
    """
    if not async_session_factory:
        raise RuntimeError(
            "Database session factory not initialized. "
            "Ensure the application has started."
        )
    return async_session_factory()


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
app.include_router(marketing_router)
app.include_router(marketing_ws_router)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy"
    }


# Authentication endpoint
@app.post("/api/login", response_model=LoginResponse)
async def login(credentials: LoginRequest) -> LoginResponse:
    """
    Login endpoint to authenticate users and receive bearer token.

    Supports two user roles:
    - admin: Can see all stores
    - store_manager: Can only see their assigned store
    """
    token, user = await authenticate_user(
        credentials.username,
        credentials.password
    )

    # Get store name if store manager
    store_name = None
    if user.store_id:
        store_name = await get_store_name(user.store_id)
    if user.customer_id:
        name = await get_user_name(user.customer_id)
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
async def get_stores() -> StoreList:
    """
    Get all store locations with inventory counts and details.
    Returns comprehensive store information for the stores page.
    """
    try:
        async with get_db_session() as session:
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
async def get_categories() -> CategoryList:
    """
    Get all product categories.
    Returns a list of all available categories in the system.
    """
    try:
        async with get_db_session() as session:
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


# Featured products endpoint
@app.get("/api/products/featured", response_model=ProductList)
@cache(expire=600)
async def get_featured_products(
    limit: int = Query(
        8, ge=1, le=50, description="Number of products to return")
) -> ProductList:
    """
    Get featured products for the homepage.
    Returns a curated selection of products with good ratings and availability.
    """
    try:
        async with get_db_session() as session:
            # Query for featured products
            # Strategy: Get products with good variety across categories
            # Prefer products with higher margins (more popular/profitable)
            # Exclude discontinued items
            stmt = (
                select(
                    ProductModel.product_id,
                    ProductModel.sku,
                    ProductModel.product_name,
                    CategoryModel.category_name,
                    ProductTypeModel.type_name,
                    ProductModel.base_price.label('unit_price'),
                    ProductModel.cost,
                    ProductModel.gross_margin_percent,
                    ProductModel.product_description,
                    SupplierModel.supplier_name,
                    ProductModel.discontinued,
                    ProductModel.image_url
                )
                .join(CategoryModel, ProductModel.category_id == CategoryModel.category_id)
                .join(ProductTypeModel, ProductModel.type_id == ProductTypeModel.type_id)
                .outerjoin(SupplierModel, ProductModel.supplier_id == SupplierModel.supplier_id)
                .where(ProductModel.discontinued == False)
                .order_by(ProductModel.gross_margin_percent.desc(), func.random())
                .limit(limit)
            )

            result = await session.execute(stmt)
            rows = result.all()

            products = []
            for row in rows:
                products.append(Product(
                    product_id=row.product_id,
                    sku=row.sku,
                    product_name=row.product_name,
                    category_name=row.category_name,
                    type_name=row.type_name,
                    unit_price=float(row.unit_price),
                    cost=float(row.cost),
                    gross_margin_percent=float(row.gross_margin_percent),
                    product_description=row.product_description,
                    supplier_name=row.supplier_name,
                    discontinued=row.discontinued,
                    image_url=row.image_url
                ))

            logger.info(f"Retrieved {len(products)} featured products")

            return ProductList(
                products=products,
                total=len(products)
            )

    except Exception as e:
        logger.error(f"Error fetching featured products: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch featured products: {str(e)}"
        )


# Get products by category endpoint
@app.get("/api/products/category/{category}", response_model=ProductList)
async def get_products_by_category(
    category: str,
    limit: int = Query(50, ge=1, le=100, description="Max products to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination")
) -> ProductList:
    """
    Get products filtered by category.
    Category names: Accessories, Apparel - Bottoms, Apparel - Tops, Footwear, Outerwear
    """
    try:
        async with get_db_session() as session:
            # Get total products in category for pagination
            total_stmt = (
                select(func.count())
                .select_from(ProductModel)
                .join(CategoryModel, ProductModel.category_id == CategoryModel.category_id)
                .where(ProductModel.discontinued == False)
                .where(func.lower(CategoryModel.category_name) == func.lower(category))
            )
            total_result = await session.execute(total_stmt)
            total_count = total_result.scalar()

            if not total_count:
                raise HTTPException(
                    status_code=404,
                    detail=f"No products found in category '{category}'"
                )

            # Query products by category
            stmt = (
                select(
                    ProductModel.product_id,
                    ProductModel.sku,
                    ProductModel.product_name,
                    CategoryModel.category_name,
                    ProductTypeModel.type_name,
                    ProductModel.base_price.label('unit_price'),
                    ProductModel.cost,
                    ProductModel.gross_margin_percent,
                    ProductModel.product_description,
                    SupplierModel.supplier_name,
                    ProductModel.discontinued,
                    ProductModel.image_url
                )
                .join(CategoryModel, ProductModel.category_id == CategoryModel.category_id)
                .join(ProductTypeModel, ProductModel.type_id == ProductTypeModel.type_id)
                .outerjoin(SupplierModel, ProductModel.supplier_id == SupplierModel.supplier_id)
                .where(ProductModel.discontinued == False)
                .where(func.lower(CategoryModel.category_name) == func.lower(category))
                .order_by(ProductModel.product_name)
                .limit(limit)
                .offset(offset)
            )

            result = await session.execute(stmt)
            rows = result.all()

            products = []
            for row in rows:
                products.append(Product(
                    product_id=row.product_id,
                    sku=row.sku,
                    product_name=row.product_name,
                    category_name=row.category_name,
                    type_name=row.type_name,
                    unit_price=float(row.unit_price),
                    cost=float(row.cost),
                    gross_margin_percent=float(row.gross_margin_percent),
                    product_description=row.product_description,
                    supplier_name=row.supplier_name,
                    discontinued=row.discontinued,
                    image_url=row.image_url
                ))

            logger.info(
                f"Retrieved {len(products)} products for category '{category}'"
            )

            return ProductList(
                products=products,
                total=total_count
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching products by category: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch products: {str(e)}"
        )


# Get product by ID endpoint
@app.get("/api/products/{product_id}", response_model=Product)
async def get_product_by_id(product_id: int) -> Product:
    """
    Get a single product by its ID.
    Returns complete product information including category, type, and supplier.
    """
    try:
        async with get_db_session() as session:
            # Query single product by ID
            stmt = (
                select(
                    ProductModel.product_id,
                    ProductModel.sku,
                    ProductModel.product_name,
                    CategoryModel.category_name,
                    ProductTypeModel.type_name,
                    ProductModel.base_price.label('unit_price'),
                    ProductModel.cost,
                    ProductModel.gross_margin_percent,
                    ProductModel.product_description,
                    SupplierModel.supplier_name,
                    ProductModel.discontinued,
                    ProductModel.image_url
                )
                .join(CategoryModel, ProductModel.category_id == CategoryModel.category_id)
                .join(ProductTypeModel, ProductModel.type_id == ProductTypeModel.type_id)
                .outerjoin(SupplierModel, ProductModel.supplier_id == SupplierModel.supplier_id)
                .where(ProductModel.product_id == product_id)
            )

            result = await session.execute(stmt)
            row = result.first()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product with ID {product_id} not found"
                )

            product = Product(
                product_id=row.product_id,
                sku=row.sku,
                product_name=row.product_name,
                category_name=row.category_name,
                type_name=row.type_name,
                unit_price=float(row.unit_price),
                cost=float(row.cost),
                gross_margin_percent=float(row.gross_margin_percent),
                product_description=row.product_description,
                supplier_name=row.supplier_name,
                discontinued=row.discontinued,
                image_url=row.image_url
            )

            logger.info(
                f"Retrieved product {product_id}: {product.product_name}")

            return product

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch product: {str(e)}"
        )


@app.get("/api/products/sku/{sku}", response_model=Product)
async def get_product_by_sku(sku: str) -> Product:
    """
    Get a single product by its SKU.
    Returns complete product information including category, type, and supplier.
    """
    try:
        async with get_db_session() as session:
            # Query single product by SKU
            stmt = (
                select(
                    ProductModel.product_id,
                    ProductModel.sku,
                    ProductModel.product_name,
                    CategoryModel.category_name,
                    ProductTypeModel.type_name,
                    ProductModel.base_price.label('unit_price'),
                    ProductModel.cost,
                    ProductModel.gross_margin_percent,
                    ProductModel.product_description,
                    SupplierModel.supplier_name,
                    ProductModel.discontinued,
                    ProductModel.image_url
                )
                .join(CategoryModel, ProductModel.category_id == CategoryModel.category_id)
                .join(ProductTypeModel, ProductModel.type_id == ProductTypeModel.type_id)
                .outerjoin(SupplierModel, ProductModel.supplier_id == SupplierModel.supplier_id)
                .where(ProductModel.sku == sku)
            )

            result = await session.execute(stmt)
            row = result.first()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product with SKU '{sku}' not found"
                )

            product = Product(
                product_id=row.product_id,
                sku=row.sku,
                product_name=row.product_name,
                category_name=row.category_name,
                type_name=row.type_name,
                unit_price=float(row.unit_price),
                cost=float(row.cost),
                gross_margin_percent=float(row.gross_margin_percent),
                product_description=row.product_description,
                supplier_name=row.supplier_name,
                discontinued=row.discontinued,
                image_url=row.image_url
            )

            logger.info(
                f"Retrieved product by SKU {sku}: {product.product_name}")

            return product

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching product by SKU {sku}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch product: {str(e)}"
        )


@app.get("/api/users/profile", response_model=CustomerProfile)
async def get_user_profile(
    current_user: TokenData = Depends(get_current_user)
) -> CustomerProfile:
    """
    Get profile information for the authenticated customer user.
    Requires authentication with customer role.
    Returns customer details including name, email, and primary store.
    """
    try:
        # Verify user has customer role and customer_id
        if current_user.user_role != "customer":
            raise HTTPException(
                status_code=403,
                detail="Only customers can access this endpoint"
            )
        
        if not current_user.customer_id:
            raise HTTPException(
                status_code=403,
                detail="Customer ID not found in token"
            )
        
        async with get_db_session() as session:
            # Query customer profile
            stmt = (
                select(
                    CustomerModel.customer_id,
                    CustomerModel.first_name,
                    CustomerModel.last_name,
                    CustomerModel.email,
                    CustomerModel.phone,
                    CustomerModel.primary_store_id,
                    StoreModel.store_name
                )
                .outerjoin(
                    StoreModel,
                    CustomerModel.primary_store_id == StoreModel.store_id
                )
                .where(CustomerModel.customer_id == current_user.customer_id)
            )

            result = await session.execute(stmt)
            row = result.first()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail="Customer profile not found"
                )

            profile = CustomerProfile(
                customer_id=row.customer_id,
                first_name=row.first_name,
                last_name=row.last_name,
                email=row.email,
                phone=row.phone,
                primary_store_id=row.primary_store_id,
                primary_store_name=row.store_name
            )

            logger.info(
                f"Retrieved profile for customer {current_user.username}"
            )

            return profile

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error fetching profile for user {current_user.username}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch profile: {str(e)}"
        )


@app.get("/api/users/orders", response_model=OrderListResponse)
async def get_user_orders(
    current_user: TokenData = Depends(get_current_user)
) -> OrderListResponse:
    """
    Get all orders for the authenticated customer user.
    Requires authentication with customer role.
    Returns orders sorted by date (newest first) with all order items.
    """
    try:
        # Verify user has customer role and customer_id
        if current_user.user_role != "customer":
            raise HTTPException(
                status_code=403,
                detail="Only customers can access this endpoint"
            )

        if not current_user.customer_id:
            raise HTTPException(
                status_code=403,
                detail="Customer ID not found in token"
            )

        async with get_db_session() as session:
            orders = await get_customer_orders(
                customer_id=current_user.customer_id,
                session=session
            )

        return orders

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error fetching orders for user {current_user.username}: {e}"
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch orders: {str(e)}"
        )


@app.get("/api/management/dashboard/top-categories", response_model=TopCategoryList)
@cache(expire=600)
async def get_top_categories(
    limit: int = Query(5, ge=1, le=10, description="Number of top categories to return"),
    current_user: TokenData = Depends(get_current_user)
) -> TopCategoryList:
    """
    Get top categories by total inventory value (cost * stock).
    Returns categories ranked by revenue potential.
    Requires authentication. Store managers see only their store's data.
    """
    try:
        async with get_db_session() as session:
            logger.info(
                f"Fetching top {limit} categories by inventory value for user {current_user.username}...")

            stmt = (
                select(
                    CategoryModel.category_name,
                    func.count(func.distinct(ProductModel.product_id)).label(
                        'product_count'),
                    func.sum(InventoryModel.stock_level).label('total_stock'),
                    func.sum(InventoryModel.stock_level *
                             ProductModel.cost).label('total_cost_value'),
                    func.sum(InventoryModel.stock_level *
                             ProductModel.base_price).label('total_retail_value'),
                    func.sum(InventoryModel.stock_level * (ProductModel.base_price -
                             ProductModel.cost)).label('potential_profit')
                )
                .select_from(InventoryModel)
                .join(ProductModel, InventoryModel.product_id == ProductModel.product_id)
                .join(CategoryModel, ProductModel.category_id == CategoryModel.category_id)
                .where(ProductModel.discontinued == False)
            )

            # Apply store filter for store managers
            if current_user.store_id is not None:
                stmt = stmt.where(InventoryModel.store_id == current_user.store_id)

            stmt = (
                stmt.group_by(CategoryModel.category_name)
                .order_by(func.sum(InventoryModel.stock_level * ProductModel.base_price).desc())
                .limit(limit)
            )

            result = await session.execute(stmt)
            rows = result.all()

            if not rows:
                return TopCategoryList(
                    categories=[],
                    total=0,
                    max_value=0.0
                )

            # Calculate max value for percentage calculation
            max_value = float(rows[0].total_retail_value) if rows else 0

            categories: list[TopCategory] = []
            for row in rows:
                retail_value = float(row.total_retail_value)
                percentage = round(
                    (retail_value / max_value * 100), 1) if max_value > 0 else 0

                categories.append(TopCategory(
                    name=row.category_name,
                    revenue=round(retail_value, 2),
                    percentage=percentage,
                    product_count=int(row.product_count),
                    total_stock=int(row.total_stock),
                    cost_value=round(float(row.total_cost_value), 2),
                    potential_profit=round(float(row.potential_profit), 2)
                ))

            logger.info(f"Retrieved {len(categories)} categories")

            return TopCategoryList(
                categories=categories,
                total=len(categories),
                max_value=round(max_value, 2)
            )

    except Exception as e:
        logger.error(f"Error fetching top categories: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch top categories: {str(e)}"
        )

@app.get("/api/management/insights", response_model=WeeklyInsights, response_model_exclude_none=False)
async def get_weekly_insights(
    store_id: Optional[int] = Query(
        None,
        ge=1,
        description="Store ID to generate insights for (admins only)",
    ),
    force_refresh: bool = Query(
        False,
        description="Force regenerate insights, bypassing cache"
    ),
    current_user: TokenData = Depends(get_current_user)
) -> WeeklyInsights:
    """
    Get AI-generated weekly insights for the management dashboard.
    Returns cached insights if available and valid (< 7 days old).
    Set force_refresh=true to bypass cache and regenerate.
    Requires authentication.
    """
    try:
        logger.info(
            "Fetching weekly insights for user %s (role=%s, store=%s, force_refresh=%s)",
            current_user.username,
            current_user.user_role,
            current_user.store_id,
            force_refresh,
        )

        # Determine which store the workflow should focus on.
        if current_user.store_id is not None:
            # Store manager - use their assigned store
            target_store_id = current_user.store_id
            if store_id and store_id != current_user.store_id:
                logger.info(
                    "Store manager attempted to request store %s; enforcing assigned store %s.",
                    store_id,
                    current_user.store_id,
                )
        elif current_user.user_role == "admin":
            # Admin - use cache key 0 for enterprise-wide insights
            target_store_id = 0
        else:
            # Fallback for other roles
            target_store_id = store_id if store_id is not None else 0

        # Check cache first unless force refresh is requested
        cache = get_cache()
        if not force_refresh:
            cached_data = cache.get(target_store_id)
            if cached_data:
                logger.info(f"Returning cached insights for store {target_store_id}")
                return WeeklyInsights.model_validate(cached_data)

        # Cache miss or force refresh - generate new insights
        logger.info(f"Generating fresh insights for store {target_store_id}")

        # Select workflow based on user role
        if current_user.user_role == "admin":
            # Admin users get enterprise-wide insights
            logger.info("Using admin insights workflow for enterprise analysis")
            workflow = admin_insights_workflow
            agent_input = (
                f"Generate admin weekly insights:\n"
                f"User Role: {current_user.user_role}\n"
                f"Days Back: 30"
            )
        else:
            # Store managers get operational insights for their store
            logger.info(f"Using store manager insights workflow for store {target_store_id}")
            workflow = insights_workflow
            agent_input = (
                f"Generate weekly insights for:\n"
                f"Store ID: {target_store_id}\n"
                f"User Role: {current_user.user_role}"
            )
        
        agent_message = ChatMessage(role="user", text=agent_input)

        insights_result: Optional[WeeklyInsights] = None
        fallback_payload: Optional[str] = None

        async for event in workflow.run_stream(agent_message):
            if isinstance(event, ExecutorFailedEvent):
                logger.error(
                    "Insights workflow failed in executor %s: %s",
                    event.executor_id,
                    event.details.message,
                )
                fallback_payload = event.details.message or "Insights workflow failed"
                break

            if isinstance(event, WorkflowOutputEvent):
                payload = event.data
                if isinstance(payload, BaseModel):
                    payload = payload.model_dump()

                if isinstance(payload, dict):
                    insights_result = WeeklyInsights.model_validate(payload)
                else:
                    fallback_payload = str(payload)
                break

        if insights_result:
            logger.info(
                "Generated dynamic weekly insights for user %s (store_id=%s)",
                current_user.username,
                target_store_id,
            )
            # Cache the successful result (include None values so frontend gets all fields)
            cache.set(target_store_id, insights_result.model_dump(exclude_none=False))
            return insights_result

        if fallback_payload:
            logger.warning(
                "Insights workflow returned non-structured payload: %s",
                fallback_payload,
            )
            return WeeklyInsights(
                store_id=target_store_id,
                summary="Dynamic insights are temporarily unavailable.",
                weather_summary="Weather data unavailable at this time.",
                events_summary=None,
                stock_items=[],
                insights=[
                    Insight(
                        type="warning",
                        title="Insights Service Unavailable",
                        description=fallback_payload,
                        action=None,
                    )
                ],
                unified_action=None,
            )

        raise HTTPException(
            status_code=502,
            detail="Insights workflow did not return data",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching weekly insights: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch weekly insights: {str(e)}"
        )


@app.delete("/api/management/insights/cache", response_model=CacheInvalidationResponse)
async def invalidate_insights_cache(
    store_id: Optional[int] = Query(
        None,
        ge=1,
        description="Store ID to invalidate cache for. If not provided, invalidates all caches."
    ),
    current_user: TokenData = Depends(get_current_user)
) -> CacheInvalidationResponse:
    """
    Invalidate insights cache (admin only).
    If store_id is provided, invalidates cache for that store only.
    Otherwise, invalidates all cached insights.
    """
    # Check admin role
    if current_user.user_role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    try:
        cache = get_cache()
        
        if store_id:
            success = cache.invalidate(store_id)
            if success:
                return CacheInvalidationResponse(
                    success=True,
                    message=f"Cache invalidated for store {store_id}",
                    store_id=store_id,
                )
            else:
                return CacheInvalidationResponse(
                    success=False,
                    message=f"No cache found for store {store_id}",
                    store_id=store_id,
                )
        else:
            count = cache.invalidate_all()
            return CacheInvalidationResponse(
                success=True,
                message=f"Invalidated {count} cached insights",
                store_id=None,
            )
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to invalidate cache: {str(e)}"
        )


@app.get("/api/management/insights/cache/info", response_model=CacheInfoResponse)
async def get_insights_cache_info(
    store_id: int = Query(
        ...,
        ge=1,
        description="Store ID to get cache info for"
    ),
    current_user: TokenData = Depends(get_current_user)
) -> CacheInfoResponse:
    """
    Get cache metadata for a specific store (admin only).
    Returns cache status, age, and validity information.
    """
    # Check admin role
    if current_user.user_role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )
    
    try:
        cache = get_cache()
        info = cache.get_cache_info(store_id)
        
        if info:
            return CacheInfoResponse(
                success=True,
                cache_info=info,
                message=None,
            )
        else:
            return CacheInfoResponse(
                success=False,
                message=f"No cache found for store {store_id}",
                cache_info=None,
            )
    except Exception as e:
        logger.error(f"Error getting cache info: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cache info: {str(e)}"
        )

        


@app.get("/api/management/suppliers", response_model=SupplierList)
async def get_suppliers(current_user: TokenData = Depends(get_current_user)) -> SupplierList:
    """
    Get all suppliers with their details and associated product categories.
    Returns comprehensive supplier information for management interface.
    Requires authentication. Store managers see only suppliers for products in their store.
    """
    try:
        async with get_db_session() as session:
            logger.info(f"Fetching suppliers for user {current_user.username}...")

            # Get basic supplier info
            stmt = (
                select(
                    SupplierModel.supplier_id,
                    SupplierModel.supplier_name,
                    SupplierModel.supplier_code,
                    SupplierModel.contact_email,
                    SupplierModel.contact_phone,
                    SupplierModel.city,
                    SupplierModel.state_province,
                    SupplierModel.payment_terms,
                    SupplierModel.lead_time_days,
                    SupplierModel.minimum_order_amount,
                    SupplierModel.bulk_discount_percent,
                    SupplierModel.supplier_rating,
                    SupplierModel.esg_compliant,
                    SupplierModel.approved_vendor,
                    SupplierModel.preferred_vendor,
                    SupplierModel.active_status
                )
                .where(SupplierModel.active_status == True)
            )
            
            # If store manager, filter suppliers to only those with products in their store
            if current_user.store_id is not None:
                # Subquery to get supplier IDs for products in the manager's store
                supplier_subquery = (
                    select(func.distinct(ProductModel.supplier_id))
                    .select_from(InventoryModel)
                    .join(ProductModel, InventoryModel.product_id == ProductModel.product_id)
                    .where(InventoryModel.store_id == current_user.store_id)
                    .where(ProductModel.supplier_id.isnot(None))
                )
                stmt = stmt.where(SupplierModel.supplier_id.in_(supplier_subquery))
            
            stmt = stmt.order_by(
                    SupplierModel.preferred_vendor.desc(),
                    SupplierModel.supplier_rating.desc(),
                    SupplierModel.supplier_name
                )

            result = await session.execute(stmt)
            rows = result.all()

            suppliers: list[Supplier] = []
            for row in rows:
                # Get categories for this supplier
                cat_stmt = (
                    select(func.distinct(CategoryModel.category_name))
                    .select_from(ProductModel)
                    .join(CategoryModel, ProductModel.category_id == CategoryModel.category_id)
                    .where(ProductModel.supplier_id == row.supplier_id)
                )
                cat_result = await session.execute(cat_stmt)
                categories = [cat_row[0] for cat_row in cat_result.all()]

                # Format location
                location = (
                    f"{row.city}, {row.state_province}"
                    if row.city else "N/A"
                )

                suppliers.append(Supplier(
                    id=row.supplier_id,
                    name=row.supplier_name,
                    code=row.supplier_code,
                    location=location,
                    contact=row.contact_email,
                    phone=row.contact_phone or "N/A",
                    rating=float(
                        row.supplier_rating) if row.supplier_rating else 0.0,
                    esg_compliant=row.esg_compliant,
                    approved=row.approved_vendor,
                    preferred=row.preferred_vendor,
                    categories=categories,
                    lead_time=row.lead_time_days,
                    payment_terms=row.payment_terms,
                    min_order=float(
                        row.minimum_order_amount) if row.minimum_order_amount else 0.0,
                    bulk_discount=float(
                        row.bulk_discount_percent) if row.bulk_discount_percent else 0.0
                ))

            logger.info(f"Retrieved {len(suppliers)} suppliers")

            return SupplierList(
                suppliers=suppliers,
                total=len(suppliers)
            )

    except Exception as e:
        logger.error(f"Error fetching suppliers: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch suppliers: {str(e)}"
        )


@app.get("/api/management/inventory", response_model=InventoryResponse)
async def get_inventory(
    store_id: Optional[int] = None,
    product_id: Optional[int] = None,
    category: Optional[str] = None,
    low_stock_only: bool = False,
    low_stock_threshold: int = 10,
    limit: int = 100,
    current_user: TokenData = Depends(get_current_user)
) -> InventoryResponse:
    """
    Get inventory levels across stores with product and category details.
    Requires authentication. Store managers automatically see only their store's inventory.

    Args:
        store_id: Optional filter by specific store (admin only)
        product_id: Optional filter by specific product
        category: Optional filter by product category
        low_stock_only: Show only items with stock below reorder threshold
        low_stock_threshold: Threshold for considering stock as low (default: 10)
        limit: Maximum number of records to return
    """
    try:
        async with get_db_session() as session:
            logger.info(
                f"Fetching inventory (store={store_id}, product={product_id}, category={category}, low_stock={low_stock_only})...")

            # Build base query with joins
            base_stmt = (
                select(InventoryModel, StoreModel, ProductModel, CategoryModel,
                       ProductTypeModel, SupplierModel)
                .select_from(InventoryModel)
                .join(StoreModel, InventoryModel.store_id == StoreModel.store_id)
                .join(ProductModel, InventoryModel.product_id == ProductModel.product_id)
                .join(CategoryModel, ProductModel.category_id == CategoryModel.category_id)
                .join(ProductTypeModel, ProductModel.type_id == ProductTypeModel.type_id)
                .outerjoin(SupplierModel, ProductModel.supplier_id == SupplierModel.supplier_id)
            )

            # Apply store filter - store managers can only see their store
            if current_user.store_id is not None:
                # Store manager - override any store_id parameter
                base_stmt = base_stmt.where(StoreModel.store_id == current_user.store_id)
            elif store_id is not None:
                # Admin with store filter
                base_stmt = base_stmt.where(StoreModel.store_id == store_id)

            if product_id is not None:
                base_stmt = base_stmt.where(
                    ProductModel.product_id == product_id)

            if category:
                base_stmt = base_stmt.where(func.lower(
                    CategoryModel.category_name) == func.lower(category))

            # Summary query - get statistics across ALL matching records
            summary_stmt = (
                select(
                    func.count(func.distinct(ProductModel.product_id)).label(
                        'total_items'),
                    func.sum(case((InventoryModel.stock_level < low_stock_threshold, 1), else_=0)).label(
                        'low_stock_count'),
                    func.sum(InventoryModel.stock_level *
                             ProductModel.cost).label('total_stock_value'),
                    func.sum(InventoryModel.stock_level *
                             ProductModel.base_price).label('total_retail_value'),
                    func.avg(InventoryModel.stock_level).label(
                        'avg_stock_level')
                )
                .select_from(InventoryModel)
                .join(StoreModel, InventoryModel.store_id == StoreModel.store_id)
                .join(ProductModel, InventoryModel.product_id == ProductModel.product_id)
                .join(CategoryModel, ProductModel.category_id == CategoryModel.category_id)
                .join(ProductTypeModel, ProductModel.type_id == ProductTypeModel.type_id)
            )

            # Apply same filters to summary query
            if current_user.store_id is not None:
                # Store manager - override any store_id parameter
                summary_stmt = summary_stmt.where(
                    StoreModel.store_id == current_user.store_id)
            elif store_id is not None:
                # Admin with store filter
                summary_stmt = summary_stmt.where(
                    StoreModel.store_id == store_id)
            if product_id is not None:
                summary_stmt = summary_stmt.where(
                    ProductModel.product_id == product_id)
            if category:
                summary_stmt = summary_stmt.where(func.lower(
                    CategoryModel.category_name) == func.lower(category))

            # Execute summary query
            summary_result = await session.execute(summary_stmt)
            summary_row = summary_result.one()

            # Main query with ordering and limit
            main_stmt = base_stmt.order_by(
                InventoryModel.stock_level.asc(),
                StoreModel.store_name,
                ProductModel.product_name
            ).limit(limit)

            # Execute main query
            result = await session.execute(main_stmt)
            rows = result.all()

            inventory_items: list[InventoryItem] = []
            for row in rows:
                inventory = row[0]
                store = row[1]
                product = row[2]
                category_obj = row[3]
                product_type = row[4]
                supplier = row[5]

                stock_level = inventory.stock_level
                reorder_point = low_stock_threshold
                is_low_stock = stock_level < reorder_point

                # Skip if filtering for low stock only
                if low_stock_only and not is_low_stock:
                    continue

                # Calculate inventory value
                cost = float(product.cost) if product.cost else 0
                base_price = float(
                    product.base_price) if product.base_price else 0
                stock_value = cost * stock_level
                retail_value = base_price * stock_level

                # Extract location from store name
                store_location = "Online Store"
                if store.is_online:
                    store_location = "Online Warehouse"
                else:
                    # Extract location from name (e.g., "Zava Pop-Up Bellevue Square" -> "Bellevue Square")
                    name_parts = store.store_name.split('Pop-Up ')
                    if len(name_parts) > 1:
                        store_location = name_parts[1]
                    else:
                        store_location = store.store_name

                inventory_items.append(InventoryItem(
                    store_id=store.store_id,
                    store_name=store.store_name,
                    store_location=store_location,
                    is_online=store.is_online,
                    product_id=product.product_id,
                    product_name=product.product_name,
                    sku=product.sku,
                    category=category_obj.category_name,
                    type=product_type.type_name,
                    stock_level=stock_level,
                    reorder_point=reorder_point,
                    is_low_stock=is_low_stock,
                    unit_cost=cost,
                    unit_price=base_price,
                    stock_value=round(stock_value, 2),
                    retail_value=round(retail_value, 2),
                    supplier_name=supplier.supplier_name if supplier else None,
                    supplier_code=supplier.supplier_code if supplier else None,
                    lead_time=supplier.lead_time_days if supplier else None,
                    image_url=product.image_url
                ))

            # Use the summary statistics from the dedicated query
            total_items = int(
                summary_row.total_items) if summary_row.total_items else 0
            low_stock_count = int(
                summary_row.low_stock_count) if summary_row.low_stock_count else 0
            total_stock_value = float(
                summary_row.total_stock_value) if summary_row.total_stock_value else 0.0
            total_retail_value = float(
                summary_row.total_retail_value) if summary_row.total_retail_value else 0.0
            avg_stock = float(
                summary_row.avg_stock_level) if summary_row.avg_stock_level else 0.0

            logger.info(
                f"Retrieved {len(inventory_items)} inventory items (showing {len(inventory_items)} of {total_items} total, {low_stock_count} low stock)")

            return InventoryResponse(
                inventory=inventory_items,
                summary=InventorySummary(
                    total_items=total_items,
                    low_stock_count=low_stock_count,
                    total_stock_value=round(total_stock_value, 2),
                    total_retail_value=round(total_retail_value, 2),
                    avg_stock_level=round(avg_stock, 1)
                )
            )

    except Exception as e:
        logger.error(f"Error fetching inventory: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch inventory: {str(e)}"
        )


@app.get("/api/management/products", response_model=ManagementProductResponse)
async def get_products(
    category: Optional[str] = None,
    supplier_id: Optional[int] = None,
    discontinued: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: TokenData = Depends(get_current_user)
) -> ManagementProductResponse:
    """
    Get products with detailed information including pricing, suppliers, and stock status.
    Requires authentication. Store managers see only products with inventory in their store.

    Args:
        category: Filter by category name
        supplier_id: Filter by supplier
        discontinued: Filter by discontinued status
        search: Search in product name, SKU, or description
        limit: Maximum number of records
        offset: Pagination offset
    """
    try:
        async with get_db_session() as session:
            logger.info("Fetching products...")

            # Build base query
            stmt = (
                select(
                    ProductModel.product_id,
                    ProductModel.sku,
                    ProductModel.product_name,
                    ProductModel.product_description,
                    CategoryModel.category_name,
                    ProductTypeModel.type_name,
                    ProductModel.base_price,
                    ProductModel.cost,
                    ProductModel.gross_margin_percent,
                    ProductModel.discontinued,
                    SupplierModel.supplier_id,
                    SupplierModel.supplier_name,
                    SupplierModel.supplier_code,
                    SupplierModel.lead_time_days,
                    func.coalesce(func.sum(InventoryModel.stock_level), 0).label(
                        'total_stock'),
                    func.count(InventoryModel.store_id).label('store_count'),
                    ProductModel.image_url
                )
                .select_from(ProductModel)
                .join(CategoryModel, ProductModel.category_id == CategoryModel.category_id)
                .join(ProductTypeModel, ProductModel.type_id == ProductTypeModel.type_id)
                .outerjoin(SupplierModel, ProductModel.supplier_id == SupplierModel.supplier_id)
                .outerjoin(InventoryModel, ProductModel.product_id == InventoryModel.product_id)
            )

            # Store manager filtering - only show products in their store
            if current_user.store_id is not None:
                stmt = stmt.where(InventoryModel.store_id == current_user.store_id)

            # Apply filters
            if category:
                stmt = stmt.where(func.lower(
                    CategoryModel.category_name) == func.lower(category))

            if supplier_id is not None:
                stmt = stmt.where(ProductModel.supplier_id == supplier_id)

            if discontinued is not None:
                stmt = stmt.where(ProductModel.discontinued == discontinued)

            if search:
                search_pattern = f"%{search}%"
                stmt = stmt.where(
                    (func.lower(ProductModel.product_name).like(func.lower(search_pattern))) |
                    (func.lower(ProductModel.sku).like(func.lower(search_pattern))) |
                    (func.lower(ProductModel.product_description).like(
                        func.lower(search_pattern)))
                )

            # Group by all non-aggregated columns
            stmt = stmt.group_by(
                ProductModel.product_id,
                CategoryModel.category_name,
                ProductTypeModel.type_name,
                SupplierModel.supplier_id,
                SupplierModel.supplier_name,
                SupplierModel.supplier_code,
                SupplierModel.lead_time_days,
                ProductModel.image_url
            )

            # Get total count (need to count before limit/offset)
            count_stmt = select(func.count(func.distinct(
                ProductModel.product_id))).select_from(stmt.alias())
            total_result = await session.execute(count_stmt)
            total_count = total_result.scalar() or 0

            # Apply ordering and pagination
            stmt = stmt.order_by(ProductModel.product_name).limit(
                limit).offset(offset)

            result = await session.execute(stmt)
            rows = result.all()

            products = []
            for row in rows:
                base_price = float(row.base_price) if row.base_price else 0
                cost = float(row.cost) if row.cost else 0
                margin = float(
                    row.gross_margin_percent) if row.gross_margin_percent else 0
                total_stock = int(row.total_stock)

                # Calculate inventory value
                stock_value = cost * total_stock
                retail_value = base_price * total_stock

                products.append(ManagementProduct(
                    product_id=row.product_id,
                    sku=row.sku,
                    name=row.product_name,
                    description=row.product_description,
                    category=row.category_name,
                    type=row.type_name,
                    base_price=base_price,
                    cost=cost,
                    margin=margin,
                    discontinued=row.discontinued,
                    supplier_id=row.supplier_id,
                    supplier_name=row.supplier_name,
                    supplier_code=row.supplier_code,
                    lead_time=row.lead_time_days,
                    total_stock=total_stock,
                    store_count=int(row.store_count),
                    stock_value=round(stock_value, 2),
                    retail_value=round(retail_value, 2),
                    image_url=row.image_url
                ))

            logger.info(
                f"Retrieved {len(products)} products (total: {total_count})")

            return ManagementProductResponse(
                products=products,
                pagination=ProductPagination(
                    total=total_count,
                    limit=limit,
                    offset=offset,
                    has_more=(offset + len(products)) < total_count
                )
            )

    except Exception as e:
        logger.error(f"Error fetching products: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch products: {str(e)}"
        )


@app.websocket("/ws/management/ai-agent/inventory")
async def websocket_ai_agent_inventory(websocket: WebSocket):
    """
    WebSocket endpoint for AI Inventory Agent.
    Streams workflow events back to the frontend in real-time.
    Requires authentication via token in the initial message.
    Store managers automatically use their assigned store_id.
    """
    await websocket.accept()
    current_user: Optional[TokenData] = None

    try:
        # Receive the initial request from the client
        data = await websocket.receive_text()
        request_data = json.loads(data)

        # Extract and validate authentication token
        token = request_data.get('token')
        if not token:
            await websocket.send_json({
                "type": "error",
                "message": "Authentication token required",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            await websocket.close(code=1008, reason="Authentication required")
            return

        current_user = await get_current_user_from_token(token)

        input_message = request_data.get(
            'message', 'Analyze inventory and recommend restocking priorities')

        # Store managers use their assigned store_id, admins can specify or use all stores
        if current_user.store_id is not None:
            # Store manager - use their store_id
            store_id = current_user.store_id
            logger.info(
                f"Store manager detected - using store_id: {store_id}"
            )
        else:
            # Admin - can optionally specify store_id
            store_id = request_data.get('store_id')
            if store_id:
                logger.info(f"Admin specified store_id: {store_id}")
            else:
                logger.info("Admin analyzing all stores")

        logger.info(
            f"AI Agent request from {current_user.username}: "
            f"  {input_message} (store_id: {store_id})"
        )

        # Send initial acknowledgment
        await websocket.send_json({
            "type": "started",
            "message": "AI Agent workflow initiated...",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Run the workflow and stream events
        # Add store_id to the message if provided
        if store_id:
            full_message = f"{input_message}\n\nStore ID: {store_id}"
        else:
            full_message = input_message

        input: ChatMessage = ChatMessage(role='user', text=full_message)

        workflow_output = None
        try:
            async for event in stock_workflow.run_stream(input):
                now = datetime.now(timezone.utc).isoformat()
                if isinstance(event, WorkflowStartedEvent):
                    event_data = {
                        "type": "workflow_started",
                        "event": str(event.data),
                        "timestamp": now
                    }
                elif isinstance(event, WorkflowOutputEvent):
                    # Capture the workflow output (markdown result)
                    if isinstance(event.data, BaseModel):
                        workflow_output = event.data.model_dump()
                    else:
                        workflow_output = str(event.data)
                    event_data = {
                        "type": "workflow_output",
                        "event": workflow_output,
                        "timestamp": now
                    }
                elif isinstance(event, ExecutorInvokedEvent):
                    event_data = {
                        "type": "step_started",
                        "event": event.data,
                        "id": event.executor_id,
                        "timestamp": now
                    }
                elif isinstance(event, ExecutorCompletedEvent):
                    event_data = {
                        "type": "step_completed",
                        "event": event.data,
                        "id": event.executor_id,
                        "timestamp": now
                    }
                elif isinstance(event, ExecutorFailedEvent):
                    event_data = {
                        "type": "step_failed",
                        "event": event.details.message,
                        "id": event.executor_id,
                        "timestamp": now
                    }
                else:
                    # Stream each workflow event to the frontend
                    event_data = {
                        "type": "event",
                        "event": str(event),
                        "timestamp": now
                    }
                await websocket.send_json(event_data)
                logger.info(f"📤 Sent event: {event}")

            # Send completion message with the workflow output
            await websocket.send_json({
                "type": "completed",
                "message": "Workflow completed successfully",
                "output": workflow_output,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            logger.info("AI Agent workflow completed")

        except Exception as workflow_error:
            logger.error(f"Workflow error: {workflow_error}")
            await websocket.send_json({
                "type": "error",
                "message": f"Workflow error: {str(workflow_error)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

    except WebSocketDisconnect:
        logger.info("🔌 WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
                "timestamp": None
            })
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass


# Root endpoint
@app.get("/")
@cache(expire=600)
async def root():
    """Root endpoint"""
    return {
        "service": "Popup Store API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "stores": "/api/stores",
            "categories": "/api/categories",
            "featured_products": "/api/products/featured",
            "products_by_category": "/api/products/category/{category}",
            "product_by_id": "/api/products/{product_id}",
            "top_categories": "/api/management/dashboard/top-categories",
            "suppliers": "/api/management/suppliers",
            "inventory": "/api/management/inventory",
            "products": "/api/management/products",
            "ai_agent_inventory": "ws://localhost:8091/ws/ai-agent/inventory (WebSocket)",
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8091,
        log_level="info"
    )

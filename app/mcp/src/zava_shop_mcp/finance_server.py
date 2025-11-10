#!/usr/bin/env python3
"""
Finance Agent MCP Server for Zava Retail

This MCP server provides finance-related tools and operations to support
finance agents with order policies, contracts, sales analysis, and inventory.

The server uses pre-written SQL queries (not dynamically generated SQL) with SQLite ORM.
"""
from opentelemetry.instrumentation.auto_instrumentation import initialize
initialize()
from datetime import datetime, timedelta
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp import FastMCP
from typing import AsyncIterator, Optional, Union
from datetime import datetime, UTC
import logging

from zava_shop_shared.finance_sqlite import FinanceSQLiteProvider
import os
from contextlib import asynccontextmanager
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from opentelemetry.instrumentation.mcp import McpInstrumentor
McpInstrumentor().instrument()
from pydantic import Field
from typing import Annotated
from sqlalchemy import select, func, case, and_

from zava_shop_shared.models.sqlite import (
    CompanyPolicy,
    Supplier,
    SupplierContract,
    Store,
    Order,
    OrderItem,
    Product,
    Category,
    ProductType,
    Inventory,
)
from zava_shop_mcp.models import (
    CompanyPolicyResult,
    SupplierContractResult,
    SalesDataResult,
    TopProductSalesResult,
    InventoryStatusResult,
    StoreResult,
)

GUEST_TOKEN = os.getenv("DEV_GUEST_TOKEN", "dev-guest-token")

verifier = StaticTokenVerifier(
    tokens={
        GUEST_TOKEN: {
            "client_id": "guest-user",
            "scopes": ["read:data"]
        }
    },
    required_scopes=["read:data"]
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

db: FinanceSQLiteProvider = FinanceSQLiteProvider()

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator:
    yield
    db.close_engine()



# Initialize FastMCP server
mcp = FastMCP("Zava Finance Agent MCP Server", auth=verifier, lifespan=app_lifespan)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> Response:
    return JSONResponse({"status": "ok"})

@mcp.tool()
async def get_company_order_policy(
    department: Annotated[Optional[str], Field(description="Department name to filter policies")] = None
) -> list[CompanyPolicyResult]:
    """
    Get company order processing policies and budget authorization rules.

    Returns company policies related to order processing, budget authorization,
    and approval requirements. Policies can be filtered by department.

    Args:
        department: Optional department name to filter policies (e.g., "Procurement", "Finance")

    Returns:
        List of CompanyPolicyResult objects containing policy details including
        policy names, types, content, thresholds, and approval requirements.

    Example:
        >>> policies = await get_company_order_policy(department="Finance")
        >>> print(f"Found {len(policies)} policies")
        >>> for policy in policies:
        >>>     print(f"Policy: {policy.policy_name} - Type: {policy.policy_type}")
    """
    try:
        logger.info(
            f"Retrieving company order policy for department: {department}")
        await db.create_pool()
        async with db.get_session() as session:
            # Build query using ORM
            policy_description = case(
                (
                    CompanyPolicy.policy_type == "order_processing",
                    "Outlines order processing and fulfillment procedures",
                ),
                (
                    CompanyPolicy.policy_type == "budget_authorization",
                    "Specifies budget limits and authorization levels",
                ),
                (
                    CompanyPolicy.policy_type == "procurement",
                    "Covers supplier selection and procurement processes",
                ),
                else_="General company policy",
            ).label("policy_description")

            content_length = func.length(
                CompanyPolicy.policy_content
            ).label("content_length")

            stmt = select(
                CompanyPolicy.policy_id,
                CompanyPolicy.policy_name,
                CompanyPolicy.policy_type,
                CompanyPolicy.policy_content,
                CompanyPolicy.department,
                CompanyPolicy.minimum_order_threshold,
                CompanyPolicy.approval_required,
                CompanyPolicy.is_active,
                policy_description,
                content_length,
            ).where(
                and_(
                    CompanyPolicy.is_active.is_(True),
                    CompanyPolicy.policy_type.in_(
                        ["order_processing", "budget_authorization"]
                    ),
                )
            )

            if department:
                stmt = stmt.where(
                    (CompanyPolicy.department == department)
                    | (CompanyPolicy.department.is_(None))
                )

            stmt = stmt.order_by(
                CompanyPolicy.policy_type, CompanyPolicy.policy_name
            )

            result = await session.execute(stmt)
            rows = result.mappings().all()

            if not rows:
                return []

            return [CompanyPolicyResult(**row) for row in rows]
    except Exception as e:
        logger.error(f"Error in get_company_order_policy: {e}")
        raise e


@mcp.tool()
async def get_supplier_contract(
    supplier_id: Annotated[int, Field(description="The unique identifier for the supplier")]
) -> list[SupplierContractResult]:
    """
    Get supplier contract information including terms and conditions.

    Returns active contract details for a specific supplier including
    contract numbers, dates, values, payment terms, and renewal status.

    Args:
        supplier_id: The unique identifier for the supplier (required)

    Returns:
        JSON string with format: {"c": [columns], "r": [[row data]], "n": count}
        Includes contract details, dates, values, and calculated expiry information.

    Example:
        >>> result = await get_supplier_contract(supplier_id=123)
        >>> data = json.loads(result)
        >>> if data['n'] > 0:
        >>>     contract = dict(zip(data['c'], data['r'][0]))
        >>>     print(f"Contract expires in {contract['days_until_expiry']} days")
    """
    try:
        logger.info(
            f"Retrieving supplier contract for supplier_id: {supplier_id}")
        await db.create_pool()
        async with db.get_session() as session:
            # Calculate days until expiry
            current_date = func.current_date()
            days_until_expiry = case(
                (
                    SupplierContract.end_date.is_not(None),
                    func.julianday(SupplierContract.end_date)
                    - func.julianday(current_date),
                ),
                else_=None,
            ).label("days_until_expiry")

            renewal_cutoff = datetime.now() + timedelta(days=90)
            renewal_due_soon = case(
                (
                    and_(
                        SupplierContract.end_date.is_not(None),
                        SupplierContract.end_date <= renewal_cutoff.date(),
                    ),
                    True,
                ),
                else_=False,
            ).label("renewal_due_soon")

            # Build query using ORM
            stmt = select(
                Supplier.supplier_name,
                Supplier.supplier_code,
                Supplier.contact_email,
                Supplier.contact_phone,
                SupplierContract.contract_id,
                SupplierContract.contract_number,
                SupplierContract.contract_status,
                SupplierContract.start_date,
                SupplierContract.end_date,
                SupplierContract.contract_value,
                SupplierContract.payment_terms,
                SupplierContract.auto_renew,
                SupplierContract.created_at.label("contract_created"),
                days_until_expiry,
                renewal_due_soon,
            ).select_from(Supplier).outerjoin(
                SupplierContract,
                Supplier.supplier_id == SupplierContract.supplier_id,
            ).where(
                and_(
                    Supplier.supplier_id == supplier_id,
                    (SupplierContract.contract_status == "active")
                    | (SupplierContract.contract_status.is_(None)),
                )
            ).order_by(SupplierContract.start_date.desc())

            result = await session.execute(stmt)
            rows = result.mappings().all()
            return [SupplierContractResult(**row) for row in rows]

    except Exception as e:
        logger.error(f"Error in get_supplier_contract: {e}")
        raise e


@mcp.tool()
async def get_historical_sales_data(
    days_back: Annotated[int, Field(description="Number of days to look back")] = 30,
    store_id: Annotated[Optional[int], Field(description="Store ID to filter results")] = None,
    category_name: Annotated[Optional[str], Field(description="Category name to filter results")] = None
) -> list[SalesDataResult]:
    """
    Get historical sales data with revenue, order counts, and customer metrics.

    Returns comprehensive sales statistics including total revenue, order counts,
    average order values, units sold, and unique customer counts. Data can be
    filtered by store and category. Default lookback period is 90 days.

    Args:
        days_back: Number of days to look back (default: 30)
        store_id: Optional store ID to filter results
        category_name: Optional category name to filter results

    Returns:
        JSON string with format: {"c": [columns], "r": [[row data]], "n": count}
        Includes date, store, category, revenue, orders, and customer metrics.

    Example:
        >>> # Get last 30 days of sales for Electronics
        >>> result = await get_historical_sales_data(days_back=30, category_name="Electronics")
        >>> data = json.loads(result)
        >>> total_revenue = sum(row[data['c'].index('total_revenue')] for row in data['r'])
    """
    try:
        logger.info(
            f"Retrieving historical sales data for store_id: {store_id}, "
            f"category_name: {category_name}, days_back: {days_back}")
        await db.create_pool()
        async with db.get_session() as session:
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=days_back)

            # Calculate month (YYYY-MM format for better readability)
            month = func.strftime('%Y-%m', Order.order_date).label("month")

            # Build query using ORM
            stmt = select(
                month,
                Store.store_name,
                Store.is_online,
                Category.category_name,
                func.count(func.distinct(Order.order_id)).label("order_count"),
                func.sum(OrderItem.total_amount).label("total_revenue"),
                func.avg(OrderItem.total_amount).label("avg_order_value"),
                func.sum(OrderItem.quantity).label("total_units_sold"),
                func.count(func.distinct(Order.customer_id)).label(
                    "unique_customers"
                ),
            ).select_from(Order).join(
                OrderItem, Order.order_id == OrderItem.order_id
            ).join(
                Store, Order.store_id == Store.store_id
            ).join(
                Product, OrderItem.product_id == Product.product_id
            ).join(
                Category, Product.category_id == Category.category_id
            ).where(
                Order.order_date >= cutoff_date.date()
            )

            if store_id is not None:
                stmt = stmt.where(Order.store_id == store_id)

            if category_name:
                stmt = stmt.where(
                    func.upper(Category.category_name) == category_name.upper()
                )

            stmt = stmt.group_by(
                month,
                Store.store_name,
                Store.is_online,
                Category.category_name,
            ).order_by(month.desc())

            result = await session.execute(stmt)
            rows = result.mappings().all()
            return [SalesDataResult(**row) for row in rows]
    except Exception as e:
        logger.error(f"Error in get_historical_sales_data: {e}")
        raise e


@mcp.tool()
async def get_top_selling_products(
    days_back: Annotated[
        int,
        Field(gt=0, le=365, description="Number of days to look back"),
    ] = 30,
    store_id: Annotated[
        Optional[Union[int, str]],
        Field(description="Store ID to filter results (integer)")
    ] = None,
    category_name: Annotated[
        Optional[str],
        Field(description="Category name to filter results"),
    ] = None,
    limit: Annotated[
        int,
        Field(gt=0, le=50, description="Number of top products to return"),
    ] = 5
) -> list[TopProductSalesResult]:
    """
    Get top-selling products by units sold and revenue.

    Returns product-level sales data showing the best-performing products
    ranked by units sold (with revenue as a tiebreaker). Results can be
    filtered by store and category.

    Args:
        days_back: Number of days to look back (default: 30)
        store_id: Optional store ID to filter results
        category_name: Optional category name to filter results
        limit: Number of top products to return (default: 5)

    Returns:
        List of top products with product name, SKU, category, order counts,
        revenue, and units sold.

    Example:
        >>> # Get top 5 products in Accessories for store 1
        >>> result = await get_top_selling_products(
        >>>     days_back=30, store_id=1, category_name="Accessories", limit=5
        >>> )
    """
    try:
        logger.info(
            f"Retrieving top selling products for store_id: {store_id}, "
            f"category_name: {category_name}, days_back: {days_back}, limit: {limit}")
        await db.create_pool()
        async with db.get_session() as session:
            # Normalize store_id input (accept ints or numeric strings)
            store_filter_id: Optional[int] = None
            if store_id is not None:
                try:
                    store_filter_id = int(store_id)
                except (TypeError, ValueError) as conversion_error:
                    raise ValueError("store_id must be an integer value") from conversion_error

                if store_filter_id < 1:
                    raise ValueError("store_id must be greater than or equal to 1")

            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=days_back)

            # Build query using ORM - group by product
            stmt = select(
                Product.product_name,
                Product.sku,
                Category.category_name,
                func.count(func.distinct(Order.order_id)).label("order_count"),
                func.sum(OrderItem.total_amount).label("total_revenue"),
                func.sum(OrderItem.quantity).label("total_units_sold"),
            ).select_from(Order).join(
                OrderItem, Order.order_id == OrderItem.order_id
            ).join(
                Product, OrderItem.product_id == Product.product_id
            ).join(
                Category, Product.category_id == Category.category_id
            ).where(
                Order.order_date >= cutoff_date.date()
            )

            if store_filter_id is not None:
                stmt = stmt.join(Store, Order.store_id == Store.store_id)
                stmt = stmt.where(Order.store_id == store_filter_id)

            if category_name:
                stmt = stmt.where(
                    func.upper(Category.category_name) == category_name.upper()
                )

            stmt = stmt.group_by(
                Product.product_name,
                Product.sku,
                Category.category_name,
            ).order_by(
                func.sum(OrderItem.quantity).desc(),
                func.sum(OrderItem.total_amount).desc(),
            ).limit(limit)

            result = await session.execute(stmt)
            rows = result.mappings().all()
            return [TopProductSalesResult(**row) for row in rows]
    except Exception as e:
        logger.error(f"Error in get_top_selling_products: {e}")
        raise e


@mcp.tool()
async def get_current_inventory_status(
    store_id: Annotated[Optional[int], Field(description="Store ID to filter results")] = None,
    category_name: Annotated[Optional[str], Field(description="Category name to filter results")] = None,
    low_stock_threshold: Annotated[int, Field(description="Low stock threshold")] = 10
) -> list[InventoryStatusResult]:
    """
    Get current inventory status across stores with values and low stock alerts.

    Returns inventory levels, cost values, retail values, and low stock alerts
    for products across all stores. Can be filtered by store and category.
    Includes inventory value calculations and stock level warnings.

    Args:
        store_id: Optional store ID to filter results
        category_name: Optional category name to filter results
        low_stock_threshold: Stock level below which to trigger alert (default: 10)

    Returns:
        JSON string with format: {"c": [columns], "r": [[row data]], "n": count}
        Includes store, product, category, stock levels, values, and alerts.

    Example:
        >>> # Get low stock items in Electronics
        >>> result = await get_current_inventory_status(
        >>>     category_name="Electronics",
        >>>     low_stock_threshold=10
        >>> )
        >>> data = json.loads(result)
        >>> low_stock_items = [row for row in data['r']
        >>>                    if row[data['c'].index('low_stock_alert')]]
    """
    try:
        logger.info(
            f"Retrieving current inventory status for store_id: {store_id},"
            f" category_name: {category_name}, "
            f" low_stock_threshold: {low_stock_threshold}")
        await db.create_pool()
        async with db.get_session() as session:
            # Calculate inventory and retail values
            inventory_value = (
                Inventory.stock_level * Product.cost
            ).label("inventory_value")
            retail_value = (
                Inventory.stock_level * Product.base_price
            ).label("retail_value")

            # Calculate low stock alert
            low_stock_alert = case(
                (Inventory.stock_level <= low_stock_threshold, True),
                else_=False,
            ).label("low_stock_alert")

            # Build query using ORM
            stmt = select(
                Store.store_name,
                Store.is_online,
                Product.product_name,
                Product.sku,
                Category.category_name,
                ProductType.type_name.label("product_type"),
                Inventory.stock_level,
                Product.cost,
                Product.base_price,
                inventory_value,
                retail_value,
                low_stock_alert,
            ).select_from(Inventory).join(
                Store, Inventory.store_id == Store.store_id
            ).join(
                Product, Inventory.product_id == Product.product_id
            ).join(
                Category, Product.category_id == Category.category_id
            ).join(
                ProductType, Product.type_id == ProductType.type_id
            ).where(
                Product.discontinued.is_(False)
            )

            if store_id is not None:
                stmt = stmt.where(Inventory.store_id == store_id)

            if category_name:
                stmt = stmt.where(
                    func.upper(Category.category_name) == category_name.upper()
                )

            stmt = stmt.order_by(
                Store.store_name,
                Category.category_name,
                Inventory.stock_level.asc(),
            )

            result = await session.execute(stmt)
            rows = result.mappings().all()
            return [InventoryStatusResult(**row) for row in rows]
    except Exception as e:
        logger.error(f"Error in get_current_inventory_status: {e}")
        raise e


@mcp.tool()
async def get_stores(
    store_name: Annotated[Optional[str], Field(description="Store name to filter results")] = None
) -> list[StoreResult]:
    """
    Get store information with optional filtering by name.

    Returns store details including store IDs, names, and online status.
    Can be filtered by store name using partial, case-insensitive matching.
    Returns all stores if no filter is provided.

    Args:
        store_name: Optional store name to search for (partial match, case-insensitive)

    Returns:
        JSON string with format: {"c": [columns], "r": [[row data]], "n": count}
        Includes store_id, store_name, is_online, rls_user_id.

    Example:
        >>> # Get all stores
        >>> result = await get_stores()
        >>> data = json.loads(result)
        >>> store_ids = [row[data['c'].index('store_id')] for row in data['r']]
        >>> # Search by name
        >>> result = await get_stores(store_name="Downtown")
        >>> # Get online stores
        >>> result = await get_stores(store_name="Online")
    """
    try:
        await db.create_pool()
        async with db.get_session() as session:
            # Build query using ORM
            stmt = select(
                Store.store_id,
                Store.store_name,
                Store.is_online,
            )

            # Apply filter if provided
            if store_name:
                stmt = stmt.where(
                    func.upper(Store.store_name).like(f"%{store_name.upper()}%")
                )

            stmt = stmt.order_by(Store.store_name)

            result = await session.execute(stmt)
            rows = result.mappings().all()
            return [StoreResult(**row) for row in rows]
    except Exception as e:
        logger.error(f"Error in get_stores: {e}")
        raise e


@mcp.tool()
async def get_current_utc_date() -> str:
    """
    Get the current date and time in UTC format.

    Useful for calculating date ranges, tracking when analyses were performed,
    and providing context for time-sensitive financial data.

    Returns:
        ISO 8601 formatted UTC datetime string (YYYY-MM-DDTHH:MM:SS.ffffffZ)

    Example:
        >>> current_time = await get_current_utc_date()
        >>> print(f"Analysis performed at: {current_time}")
    """
    try:
        return datetime.now(UTC).isoformat()
    except Exception as e:
        logger.error(f"Error getting current UTC date: {e}")
        raise e

if __name__ == "__main__":
    logger.info("🚀 Starting Supplier Agent MCP Server")
    # Configure server settings
    port = int(os.getenv("PORT", 8002))
    host = os.getenv("HOST", "0.0.0.0")  # noqa: S104
    logger.info(
        "❤️ 📡 Supplier MCP endpoint starting at: http://%s:%d/mcp",
        host,
        port,
    )
    logger.info("Guest token is '%s******%s'", GUEST_TOKEN[0:1], GUEST_TOKEN[-2:])
    mcp.run(transport="http", host=host, port=port, path="/mcp", stateless_http=True)

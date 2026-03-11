#!/usr/bin/env python3
"""
Customer MCP Server for Zava Retail

This MCP server provides customer-facing tools scoped to the logged-in user:
1. Get my orders - returns orders for the authenticated customer
2. Search products - browse the product catalog

Uses OAuth 2.0 with Dynamic Client Registration (DCR) via Keycloak.
The customer_id is extracted from the JWT access token claims — tool
callers cannot override it.
"""
import os

if os.environ.get("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    from azure.monitor.opentelemetry import configure_azure_monitor
    configure_azure_monitor()
else:
    # Local dev: use generic OTLP exporter (Aspire collector on localhost:4317)
    from opentelemetry.instrumentation.auto_instrumentation import initialize
    initialize()

from zava_shop_mcp.keycloak_provider import KeycloakAuthProvider
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token
from zava_shop_shared.finance_sqlite import FinanceSQLiteProvider
from pydantic import Field
from typing import Annotated, AsyncIterator
from decimal import Decimal
import logging
from contextlib import asynccontextmanager
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from sqlalchemy import select, func, or_

from zava_shop_shared.models.sqlite import (
    Category,
    Order,
    OrderItem,
    Product,
    Store,
)
from zava_shop_shared.models.results import (
    CustomerOrderItemResult,
    CustomerOrderResult,
    ProductSearchResult,
)
from opentelemetry.instrumentation.mcp import McpInstrumentor
McpInstrumentor().instrument()


logger = logging.getLogger(__name__)

db: FinanceSQLiteProvider = FinanceSQLiteProvider()


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator:
    yield
    await db.close_engine()


KEYCLOAK_REALM_URL = os.environ["KEYCLOAK_REALM_URL"]
keycloak_base_url = os.environ["KEYCLOAK_MCP_SERVER_BASE_URL"]
keycloak_audience = os.getenv("KEYCLOAK_MCP_SERVER_AUDIENCE") or "mcp-server"

auth = KeycloakAuthProvider(
    realm_url=KEYCLOAK_REALM_URL,
    base_url=keycloak_base_url,
    required_scopes=["openid", "zava:access"],
    audience=keycloak_audience,
)

# Create MCP server with lifespan support
mcp = FastMCP("mcp-zava-customer", auth=auth, lifespan=app_lifespan)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> Response:
    return JSONResponse({"status": "ok"})


def _get_customer_id_from_token() -> int:
    """Extract the customer_id claim from the current access token.

    Raises ValueError if the token is missing or does not contain a
    customer_id claim.
    """
    token = get_access_token()
    if token is None:
        raise ValueError("No access token available – request must be authenticated")
    customer_id = token.claims.get("customer_id")
    if customer_id is None:
        raise ValueError("Access token does not contain a customer_id claim")
    return int(customer_id)


@mcp.tool()
async def get_my_orders(
    limit: Annotated[
        int,
        Field(
            description="Maximum number of orders to return. Default is 10."
        ),
    ] = 10,
) -> list[CustomerOrderResult]:
    """
    Get the authenticated customer's orders.

    Returns recent orders for the logged-in customer, including order items
    with product details. The customer is identified from the OAuth access
    token — no customer_id parameter is needed or accepted.

    Returns:
        List of orders with items, most recent first.
    """
    customer_id = _get_customer_id_from_token()
    logger.info("Fetching orders for customer_id=%s (limit=%d)", customer_id, limit)

    try:
        await db.create_pool()
        async with db.get_session() as session:
            # Fetch orders for this customer, most recent first
            orders_stmt = (
                select(Order, Store.store_name)
                .join(Store, Order.store_id == Store.store_id)
                .where(Order.customer_id == customer_id)
                .order_by(Order.order_date.desc())
                .limit(limit)
            )
            orders_result = await session.execute(orders_stmt)
            order_rows = orders_result.all()

            results: list[CustomerOrderResult] = []

            for order, store_name in order_rows:
                # Fetch items for each order
                items_stmt = (
                    select(
                        OrderItem.quantity,
                        OrderItem.unit_price,
                        OrderItem.discount_percent,
                        OrderItem.discount_amount,
                        OrderItem.total_amount,
                        Product.product_name,
                        Product.sku,
                        Product.image_url,
                    )
                    .join(Product, OrderItem.product_id == Product.product_id)
                    .where(OrderItem.order_id == order.order_id)
                )
                items_result = await session.execute(items_stmt)
                item_rows = items_result.all()

                items = [
                    CustomerOrderItemResult(
                        product_name=row.product_name,
                        sku=row.sku,
                        quantity=row.quantity,
                        unit_price=Decimal(str(row.unit_price)),
                        discount_percent=row.discount_percent or 0,
                        discount_amount=Decimal(str(row.discount_amount or 0)),
                        total_amount=Decimal(str(row.total_amount)),
                        image_url=row.image_url,
                    )
                    for row in item_rows
                ]

                order_total = sum(item.total_amount for item in items)

                results.append(
                    CustomerOrderResult(
                        order_id=order.order_id,
                        order_date=str(order.order_date),
                        store_name=store_name,
                        items=items,
                        order_total=order_total,
                    )
                )

            logger.info("Returning %d orders for customer_id=%s", len(results), customer_id)
            return results

    except ValueError:
        raise
    except Exception as e:
        logger.error("Error fetching orders for customer_id=%s: %s", customer_id, e)
        raise


@mcp.tool()
async def search_products(
    query: Annotated[
        str,
        Field(
            description="Search term to match against product name or description. Leave empty to browse all products."
        ),
    ] = "",
    category: Annotated[
        str,
        Field(
            description="Category name to filter products (e.g., 'Tools', 'Hardware'). Leave empty for all categories."
        ),
    ] = "",
    limit: Annotated[
        int,
        Field(
            description="Maximum number of products to return. Default is 20."
        ),
    ] = 20,
) -> list[ProductSearchResult]:
    """
    Search the product catalog.

    Browse and search available products by name, description, or category.
    Only active (non-discontinued) products are returned.

    Returns:
        List of matching products with details and pricing.
    """
    logger.info("Searching products - query=%r, category=%r, limit=%d", query, category, limit)

    try:
        await db.create_pool()
        async with db.get_session() as session:
            stmt = (
                select(
                    Product.product_id,
                    Product.sku,
                    Product.product_name,
                    Product.base_price,
                    Product.product_description,
                    Product.image_url,
                    Category.category_name,
                )
                .join(Category, Product.category_id == Category.category_id)
                .where(Product.discontinued == False)  # noqa: E712
            )

            # Apply text search filter
            if query:
                search_pattern = f"%{query}%"
                stmt = stmt.where(
                    or_(
                        Product.product_name.ilike(search_pattern),
                        Product.product_description.ilike(search_pattern),
                    )
                )

            # Apply category filter
            if category:
                stmt = stmt.where(
                    func.lower(Category.category_name) == func.lower(category)
                )

            stmt = stmt.order_by(Product.product_name).limit(limit)

            result = await session.execute(stmt)
            rows = result.all()

            products = [
                ProductSearchResult(
                    product_id=row.product_id,
                    sku=row.sku,
                    product_name=row.product_name,
                    category_name=row.category_name,
                    base_price=Decimal(str(row.base_price)),
                    product_description=row.product_description,
                    image_url=row.image_url,
                )
                for row in rows
            ]

            logger.info("Returning %d products", len(products))
            return products

    except Exception as e:
        logger.error("Error searching products: %s", e)
        raise


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8002))
    logger.info("Starting Customer MCP server on port %d", port)
    uvicorn.run(mcp.http_app(), host="0.0.0.0", port=port)

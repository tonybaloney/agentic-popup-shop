#!/usr/bin/env python3
"""
Supplier Agent MCP Server for Zava Retail

This MCP server provides tools to support a Supplier Agent with the following capabilities:
1. Find suppliers for the request - DB query
2. Supplier history and performance - DB query  
3. Get Supplier Contract - document
4. Get Company's Supplier policy - document

Uses pre-written SQL queries from supplier_sqlite.py for all database operations.
"""

from opentelemetry.instrumentation.auto_instrumentation import initialize
initialize()
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier
from fastmcp import FastMCP
from github_shop_shared.supplier_sqlite import SupplierSQLiteProvider
from github_shop_shared.config import Config
from pydantic import Field
from typing import Annotated, AsyncIterator, Optional
import os
from datetime import datetime, timezone
import logging
from contextlib import asynccontextmanager
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

from opentelemetry.instrumentation.mcp import McpInstrumentor
McpInstrumentor().instrument()

verifier = StaticTokenVerifier(
    tokens={
        os.getenv("DEV_GUEST_TOKEN", "dev-guest-token"): {
            "client_id": "guest-user",
            "scopes": ["read:data"]
        }
    },
    required_scopes=["read:data"]
)

config = Config()
logger = logging.getLogger(__name__)

db: SupplierSQLiteProvider | None = None

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator:
    global db
    db = SupplierSQLiteProvider()
    try:
        await db.create_pool()
        yield
    finally:
        # Cleanup on shutdown
        if db:
            await db.close_engine()

# Create MCP server with lifespan support
mcp = FastMCP("mcp-zava-supplier", auth=verifier, lifespan=app_lifespan)

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> Response:
    assert db, "Server not initialized"  # noqa: S101
    return JSONResponse({"status": "ok"})

@mcp.tool()
async def find_suppliers_for_request(
    product_category: Annotated[
        Optional[str],
        Field(
            description="Product category to filter suppliers by (e.g., 'Tools', 'Hardware', 'Building Materials'). Leave empty to search all categories."
        ),
    ] = None,
    esg_required: Annotated[
        bool,
        Field(
            description="Whether ESG (Environmental, Social, Governance) compliance is required. Set to true if the request specifically requires ESG-compliant suppliers."
        ),
    ] = False,
    min_rating: Annotated[
        float,
        Field(
            description="Minimum supplier rating required (0.0 to 5.0). Default is 3.0 for acceptable quality suppliers."
        ),
    ] = 3.0,
    max_lead_time: Annotated[
        int,
        Field(
            description="Maximum acceptable lead time in days. Default is 30 days for standard procurement."
        ),
    ] = 30,
    budget_min: Annotated[
        Optional[float],
        Field(
            description="Minimum budget amount to consider suppliers with appropriate minimum order amounts."
        ),
    ] = None,
    budget_max: Annotated[
        Optional[float],
        Field(
            description="Maximum budget amount to filter suppliers by bulk discount thresholds."
        ),
    ] = None,
    limit: Annotated[
        int,
        Field(
            description="Maximum number of suppliers to return. Default is 10."
        ),
    ] = 10,
) -> str:
    """
    Find suppliers that match procurement request requirements.

    This tool searches for suppliers based on product category, ESG compliance,
    rating requirements, lead time constraints, and budget considerations.
    Returns suppliers ranked by preference and performance.

    Returns:
        JSON with supplier details including ratings, contact info, terms, and contract status.
    """

    logger.info("Finding suppliers - Category: %s, ESG: %s, Min Rating: %.1f",
                product_category, esg_required, min_rating)

    try:
        assert db, "Server not initialized"  # noqa: S101
        result = await db.find_suppliers_for_request(
            product_category=product_category,
            esg_required=esg_required,
            min_rating=min_rating,
            max_lead_time=max_lead_time,
            budget_min=budget_min,
            budget_max=budget_max,
            limit=limit
        )
        return result

    except Exception as e:
        logger.error("Find suppliers failed: %s", e)
        raise e


@mcp.tool()
async def get_supplier_history_and_performance(
    supplier_id: Annotated[
        int,
        Field(
            description="Unique identifier of the supplier to get performance history for."
        ),
    ],
    months_back: Annotated[
        int,
        Field(
            description="Number of months of history to retrieve. Default is 12 months for annual performance view."
        ),
    ] = 12,
) -> str:
    """
    Get detailed supplier performance history and metrics.

    This tool retrieves historical performance evaluations, procurement activity,
    and performance trends for a specific supplier. Includes cost, quality,
    delivery, and compliance scores over time.

    Returns:
        JSON with performance scores, evaluation dates, procurement history, and trend data.
    """

    logger.info("Getting supplier history - ID: %d, Months: %d",
                supplier_id, months_back)

    try:
        assert db, "Server not initialized"  # noqa: S101
        result = await db.get_supplier_history_and_performance(
            supplier_id=supplier_id,
            months_back=months_back
        )
        return result

    except Exception as e:
        logger.error("Get supplier history failed: %s", e)
        raise e

@mcp.tool()
async def get_supplier_contract(
    supplier_id: Annotated[
        int,
        Field(
            description="Unique identifier of the supplier to get contract information for."
        ),
    ],
) -> str:
    """
    Get supplier contract details and terms.

    This tool retrieves active contract information including contract numbers,
    terms and conditions, payment terms, contract values, expiration dates,
    and renewal information for a specific supplier.

    Returns:
        JSON with contract details, terms, values, dates, and renewal status.
    """

    logger.info("Getting supplier contract - ID: %d", supplier_id)

    try:
        assert db, "Server not initialized"  # noqa: S101
        result = await db.get_supplier_contract(supplier_id=supplier_id)
        return result

    except Exception as e:
        logger.error("Get supplier contract failed: %s", e)
        raise e


@mcp.tool()
async def get_company_supplier_policy(
    policy_type: Annotated[
        Optional[str],
        Field(
            description="Type of policy to retrieve. Options: 'procurement', 'vendor_approval', 'budget_authorization', 'order_processing'. Leave empty to get all supplier-related policies."
        ),
    ] = None,
    department: Annotated[
        Optional[str],
        Field(
            description="Department-specific policies to retrieve. Leave empty to get company-wide policies."
        ),
    ] = None,
) -> str:
    """
    Get company policies related to supplier management.

    This tool retrieves company policies and procedures for supplier selection,
    procurement processes, vendor approval requirements, and budget authorization
    limits. Helps ensure compliance with company guidelines.

    Returns:
        JSON with policy documents, procedures, requirements, and approval thresholds.
    """

    logger.info("Getting company policies - Type: %s, Department: %s",
                policy_type, department)

    try:
        assert db, "Server not initialized"  # noqa: S101
        result = await db.get_company_supplier_policy(
            policy_type=policy_type,
            department=department
        )
        return result

    except Exception as e:
        logger.error("Get company policy failed: %s", e)
        raise e


@mcp.tool()
async def get_current_utc_date() -> str:
    """Get the current UTC date and time in ISO format. Useful for date-time relative queries or understanding the current date for time-sensitive supplier analysis.

    Returns:
        Current UTC date and time in ISO format (YYYY-MM-DDTHH:MM:SS.fffffZ)
    """
    logger.info("Retrieving current UTC date and time")
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    logger.info("🚀 Starting Supplier Agent MCP Server")
    # Configure server settings
    port = int(os.getenv("PORT", 8092))
    host = os.getenv("HOST", "0.0.0.0")  # noqa: S104
    logger.info(
        "❤️ 📡 Supplier MCP endpoint starting at: http://%s:%d/mcp",
        host,
        port,
    )

    mcp.run(transport="http", host=host, port=port, path="/mcp", stateless_http=True)

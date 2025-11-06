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
from fastmcp.server.auth import AccessToken
from fastmcp import FastMCP
from zava_shop_shared.supplier_sqlite import SupplierSQLiteProvider
from pydantic import Field
from typing import Annotated, AsyncIterator, Optional
import os
from datetime import datetime, timezone, timedelta
import logging
from contextlib import asynccontextmanager
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from sqlalchemy import or_, select, func, case, and_

from zava_shop_shared.models.sqlite import (
    CompanyPolicy,
    Supplier,
    SupplierContract,
    SupplierPerformance,
    ProcurementRequest,
    Product,
    Category,
)
from zava_shop_mcp.models import (
    CompanySupplierPolicyResult,
    FindSuppliersResult,
    SupplierContractResult,
    SupplierHistoryAndPerformanceResult,
)
from opentelemetry.instrumentation.mcp import McpInstrumentor
McpInstrumentor().instrument()


GUEST_TOKEN = os.getenv("DEV_GUEST_TOKEN", "dev-guest-token")

logger = logging.getLogger(__name__)

class LoggingStaticTokenVerifier(StaticTokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        result = await super().verify_token(token)
        if not result:
            logger.warning("Could not verify token: %s******%s", token[0:1], token[-2:])
        return result

verifier = LoggingStaticTokenVerifier(
    tokens={
        GUEST_TOKEN: {
            "client_id": "guest-user",
            "scopes": ["read:data"]
        }
    },
    required_scopes=["read:data"]
)

db: SupplierSQLiteProvider = SupplierSQLiteProvider()

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator:
    yield
    await db.close_engine()

# Create MCP server with lifespan support
mcp = FastMCP("mcp-zava-supplier", auth=verifier, lifespan=app_lifespan)

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> Response:
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
) -> list[FindSuppliersResult]:
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
        await db.create_pool()
        async with db.get_session() as session:
            # Calculate average performance score
            avg_performance = func.coalesce(
                func.avg(SupplierPerformance.overall_score),
                Supplier.supplier_rating,
            ).label("avg_performance_score")

            # Count available products
            product_count = func.count(Product.product_id).label(
                "available_products"
            )

            # Build base query with joins
            stmt = select(
                Supplier.supplier_id,
                Supplier.supplier_name,
                Supplier.supplier_code,
                Supplier.contact_email,
                Supplier.contact_phone,
                Supplier.supplier_rating,
                Supplier.esg_compliant,
                Supplier.preferred_vendor,
                Supplier.approved_vendor,
                Supplier.lead_time_days,
                Supplier.minimum_order_amount,
                Supplier.bulk_discount_threshold,
                Supplier.bulk_discount_percent,
                Supplier.payment_terms,
                product_count,
                avg_performance,
                SupplierContract.contract_status,
                SupplierContract.contract_number,
                Category.category_name,
            ).select_from(Supplier).outerjoin(
                Product, Supplier.supplier_id == Product.supplier_id
            ).outerjoin(
                Category, Product.category_id == Category.category_id
            ).outerjoin(
                SupplierPerformance,
                Supplier.supplier_id == SupplierPerformance.supplier_id,
            ).outerjoin(
                SupplierContract,
                and_(
                    Supplier.supplier_id == SupplierContract.supplier_id,
                    SupplierContract.contract_status == "active",
                ),
            ).where(
                and_(
                    Supplier.active_status.is_(True),
                    Supplier.approved_vendor.is_(True),
                    Supplier.supplier_rating >= min_rating,
                    Supplier.lead_time_days <= max_lead_time,
                )
            )

            # Add ESG filter if required
            if esg_required:
                stmt = stmt.where(Supplier.esg_compliant.is_(True))

            # Add product category filter if specified
            if product_category:
                stmt = stmt.where(
                    func.upper(Category.category_name) == product_category.upper()
                )

            # Add budget filters if specified
            if budget_min is not None:
                stmt = stmt.where(Supplier.minimum_order_amount <= budget_min)

            if budget_max is not None:
                stmt = stmt.where(Supplier.bulk_discount_threshold <= budget_max)

            # Group by all non-aggregated columns
            stmt = stmt.group_by(
                Supplier.supplier_id,
                Supplier.supplier_name,
                Supplier.supplier_code,
                Supplier.contact_email,
                Supplier.contact_phone,
                Supplier.supplier_rating,
                Supplier.esg_compliant,
                Supplier.preferred_vendor,
                Supplier.approved_vendor,
                Supplier.lead_time_days,
                Supplier.minimum_order_amount,
                Supplier.bulk_discount_threshold,
                Supplier.bulk_discount_percent,
                Supplier.payment_terms,
                SupplierContract.contract_status,
                SupplierContract.contract_number,
                Category.category_name,
            ).order_by(
                Supplier.preferred_vendor.desc(),
                avg_performance.desc(),
                Supplier.supplier_rating.desc(),
            ).limit(limit)

            result = await session.execute(stmt)
            rows = result.mappings().all()

            return [FindSuppliersResult(**row) for row in rows]

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
) -> list[SupplierHistoryAndPerformanceResult]:
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
        await db.create_pool()
        async with db.get_session() as session:

            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=months_back * 30)

            # Count total requests per supplier
            total_requests = func.count(ProcurementRequest.request_id).over(
                partition_by=Supplier.supplier_id
            ).label("total_requests")

            # Sum total value per supplier
            total_value = func.sum(ProcurementRequest.total_cost).over(
                partition_by=Supplier.supplier_id
            ).label("total_value")

            # Build query with joins
            stmt = select(
                Supplier.supplier_name,
                Supplier.supplier_code,
                Supplier.supplier_rating,
                Supplier.esg_compliant,
                Supplier.preferred_vendor,
                Supplier.lead_time_days,
                Supplier.created_at.label("supplier_since"),
                SupplierPerformance.evaluation_date,
                SupplierPerformance.cost_score,
                SupplierPerformance.quality_score,
                SupplierPerformance.delivery_score,
                SupplierPerformance.compliance_score,
                SupplierPerformance.overall_score,
                SupplierPerformance.notes.label("performance_notes"),
                total_requests,
                total_value,
            ).select_from(Supplier).outerjoin(
                SupplierPerformance,
                Supplier.supplier_id == SupplierPerformance.supplier_id,
            ).outerjoin(
                ProcurementRequest,
                Supplier.supplier_id == ProcurementRequest.supplier_id,
            ).where(
                and_(
                    Supplier.supplier_id == supplier_id,
                    or_(
                        SupplierPerformance.evaluation_date >= cutoff_date.date(),
                        SupplierPerformance.evaluation_date.is_(None),
                    ),
                )
            ).order_by(SupplierPerformance.evaluation_date.desc())

            result = await session.execute(stmt)
            rows = result.mappings().all()
            return [SupplierHistoryAndPerformanceResult(**row) for row in rows]


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
) -> list[SupplierContractResult]:
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

            # Calculate renewal due soon (within 90 days)
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

            # Build query
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
                    or_(
                        SupplierContract.contract_status == "active",
                        SupplierContract.contract_status.is_(None),
                    ),
                )
            ).order_by(SupplierContract.start_date.desc())

            result = await session.execute(stmt)
            rows = result.mappings().all()
            return [SupplierContractResult(**row) for row in rows]

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
) -> list[CompanySupplierPolicyResult]:
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
        await db.create_pool()
        async with db.get_session() as session:
            # Build policy description
            policy_description = case(
                (
                    CompanyPolicy.policy_type == "procurement",
                    "Covers supplier selection and procurement processes",
                ),
                (
                    CompanyPolicy.policy_type == "vendor_approval",
                    "Defines vendor approval and onboarding requirements",
                ),
                (
                    CompanyPolicy.policy_type == "budget_authorization",
                    "Specifies budget limits and authorization levels",
                ),
                (
                    CompanyPolicy.policy_type == "order_processing",
                    "Outlines order processing and fulfillment procedures",
                ),
                else_="General company policy",
            ).label("policy_description")

            content_length = func.length(
                CompanyPolicy.policy_content
            ).label("content_length")

            # Build base query
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
            ).where(CompanyPolicy.is_active.is_(True))

            # Add filters
            if policy_type:
                stmt = stmt.where(CompanyPolicy.policy_type == policy_type)

            if department:
                stmt = stmt.where(
                    or_(
                        CompanyPolicy.department == department,
                        CompanyPolicy.department.is_(None),
                    )
                )

            stmt = stmt.order_by(
                CompanyPolicy.policy_type, CompanyPolicy.policy_name
            )

            result = await session.execute(stmt)
            rows = result.mappings().all()
            return [CompanySupplierPolicyResult(**row) for row in rows]

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
    port = int(os.getenv("PORT", 8002))
    host = os.getenv("HOST", "0.0.0.0")  # noqa: S104
    logger.info(
        "❤️ 📡 Supplier MCP endpoint starting at: http://%s:%d/mcp",
        host,
        port,
    )
    logger.info("Guest token is '%s******%s'", GUEST_TOKEN[0:1], GUEST_TOKEN[-2:])

    mcp.run(transport="http", host=host, port=port, path="/mcp")

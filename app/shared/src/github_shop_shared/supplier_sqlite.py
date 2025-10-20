#!/usr/bin/env python3
"""
Supplier Database Access Provider for Zava Retail - SQLite Edition

This module provides pre-written SQL queries for supplier-related operations
to support the Supplier Agent MCP server using SQLite with SQLAlchemy ORM.
"""

import asyncio
import json
import logging
from typing import Optional

from sqlalchemy import select, func, case, and_, or_
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker

from .config import Config
from .models.sqlite import (
    Supplier,
    SupplierContract,
    SupplierPerformance,
    ProcurementRequest,
    CompanyPolicy,
    Product,
    Category,
)

logger = logging.getLogger(__name__)
config = Config()


class SupplierSQLiteProvider:
    """Provides SQLite database access for supplier-related operations."""

    def __init__(self, sqlite_url: Optional[str] = None) -> None:
        # Use default SQLite URL if not provided
        self.sqlite_url = sqlite_url or "sqlite+aiosqlite:////workspace/data/retail.db"
        self.engine: Optional[AsyncEngine] = None
        self.async_session_factory: Optional[async_sessionmaker] = None

    async def __aenter__(self) -> "SupplierSQLiteProvider":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[object],
    ) -> None:
        """Async context manager exit."""
        await self.close_engine()

    async def create_pool(self) -> None:
        """Create async engine for database connections."""
        if self.engine is None:
            try:
                self.engine = create_async_engine(
                    self.sqlite_url,
                    connect_args={"timeout": 30, "check_same_thread": False},
                    pool_pre_ping=True,
                    echo=False,
                )

                # Create async session factory
                self.async_session_factory = async_sessionmaker(
                    self.engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                )

                logger.info("✅ Supplier SQLite async engine created")
            except Exception as e:
                logger.error("❌ Failed to create SQLAlchemy engine: %s", e)
                raise

    async def close_engine(self) -> None:
        """Close async engine and cleanup."""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.async_session_factory = None
            logger.info("✅ Supplier SQLite async engine closed")

    def get_session(self) -> AsyncSession:
        """Get a new async session."""
        if not self.async_session_factory:
            raise RuntimeError(
                "No session factory available. Call create_pool() first."
            )
        return self.async_session_factory()

    async def find_suppliers_for_request(
        self,
        product_category: Optional[str] = None,
        esg_required: bool = False,
        min_rating: float = 3.0,
        max_lead_time: int = 30,
        budget_min: Optional[float] = None,
        budget_max: Optional[float] = None,
        limit: int = 10,
    ) -> str:
        """
        Find suppliers for a request based on various criteria.

        Returns suppliers that match the specified requirements including
        product category, ESG compliance, rating, lead time, and budget constraints.
        """
        async with self.get_session() as session:
            try:
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

                if not rows:
                    return json.dumps(
                        {
                            "c": [],
                            "r": [],
                            "n": 0,
                            "msg": "No suppliers found matching criteria",
                        },
                        separators=(",", ":"),
                        default=str,
                    )

                columns = list(rows[0].keys())
                data_rows = [[row[col] for col in columns] for row in rows]

                return json.dumps(
                    {"c": columns, "r": data_rows, "n": len(data_rows)},
                    separators=(",", ":"),
                    default=str,
                )

            except Exception as e:
                return json.dumps(
                    {
                        "err": f"Find suppliers query failed: {e!s}",
                        "c": [],
                        "r": [],
                        "n": 0,
                    },
                    separators=(",", ":"),
                    default=str,
                )

    async def get_supplier_history_and_performance(
        self, supplier_id: int, months_back: int = 12
    ) -> str:
        """
        Get supplier history and performance data.

        Returns performance evaluations, recent procurement requests,
        and overall performance trends for the specified supplier.
        """
        async with self.get_session() as session:
            try:
                from datetime import datetime, timedelta

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

                if not rows:
                    return json.dumps(
                        {
                            "c": [],
                            "r": [],
                            "n": 0,
                            "msg": f"No data found for supplier ID {supplier_id}",
                        },
                        separators=(",", ":"),
                        default=str,
                    )

                columns = list(rows[0].keys())
                data_rows = [[row[col] for col in columns] for row in rows]

                return json.dumps(
                    {"c": columns, "r": data_rows, "n": len(data_rows)},
                    separators=(",", ":"),
                    default=str,
                )

            except Exception as e:
                return json.dumps(
                    {
                        "err": f"Supplier history query failed: {e!s}",
                        "c": [],
                        "r": [],
                        "n": 0,
                    },
                    separators=(",", ":"),
                    default=str,
                )

    async def get_supplier_contract(self, supplier_id: int) -> str:
        """
        Get supplier contract information.

        Returns active contract details including terms, conditions,
        and key contract metadata for the specified supplier.
        """
        async with self.get_session() as session:
            try:
                from datetime import datetime, timedelta

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

                if not rows:
                    return json.dumps(
                        {
                            "c": [],
                            "r": [],
                            "n": 0,
                            "msg": f"No contract found for supplier ID {supplier_id}",
                        },
                        separators=(",", ":"),
                        default=str,
                    )

                columns = list(rows[0].keys())
                data_rows = [[row[col] for col in columns] for row in rows]

                return json.dumps(
                    {"c": columns, "r": data_rows, "n": len(data_rows)},
                    separators=(",", ":"),
                    default=str,
                )

            except Exception as e:
                return json.dumps(
                    {
                        "err": f"Supplier contract query failed: {e!s}",
                        "c": [],
                        "r": [],
                        "n": 0,
                    },
                    separators=(",", ":"),
                    default=str,
                )

    async def get_company_supplier_policy(
        self, policy_type: Optional[str] = None, department: Optional[str] = None
    ) -> str:
        """
        Get company supplier policies.

        Returns company policies related to supplier management,
        procurement procedures, and vendor requirements.
        """
        async with self.get_session() as session:
            try:
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

                if not rows:
                    return json.dumps(
                        {
                            "c": [],
                            "r": [],
                            "n": 0,
                            "msg": "No company policies found",
                        },
                        separators=(",", ":"),
                        default=str,
                    )

                columns = list(rows[0].keys())
                data_rows = [[row[col] for col in columns] for row in rows]

                return json.dumps(
                    {"c": columns, "r": data_rows, "n": len(data_rows)},
                    separators=(",", ":"),
                    default=str,
                )

            except Exception as e:
                return json.dumps(
                    {
                        "err": f"Company policy query failed: {e!s}",
                        "c": [],
                        "r": [],
                        "n": 0,
                    },
                    separators=(",", ":"),
                    default=str,
                )


async def test_connection() -> bool:
    """Test SQLite connection and return success status."""
    try:
        provider = SupplierSQLiteProvider()
        await provider.create_pool()
        await provider.close_engine()
        return True
    except Exception as e:
        logger.error("Connection test failed: %s", e)
        return False


async def main() -> None:
    """Main function to test the supplier provider."""
    logger.info("🤖 Supplier SQLite Provider Test")
    logger.info("=" * 50)

    if not await test_connection():
        logger.error("❌ Error: Cannot connect to SQLite database")
        return

    try:
        async with SupplierSQLiteProvider() as provider:
            await provider.create_pool()

            logger.info("🧪 Testing Supplier Queries:")
            logger.info("=" * 50)

            # Test 1: Find suppliers
            logger.info("📊 Test 1: Find suppliers with ESG requirement")
            result = await provider.find_suppliers_for_request(
                esg_required=True, min_rating=4.0, limit=5
            )
            logger.info(
                "Result: %s", result[: 200] + "..." if len(result) > 200 else result
            )

            # Test 2: Get supplier performance (assuming supplier_id 1 exists)
            logger.info("📊 Test 2: Get supplier performance history")
            result = await provider.get_supplier_history_and_performance(supplier_id=1)
            logger.info(
                "Result: %s", result[: 200] + "..." if len(result) > 200 else result
            )

            # Test 3: Get supplier contract
            logger.info("📊 Test 3: Get supplier contract")
            result = await provider.get_supplier_contract(supplier_id=1)
            logger.info(
                "Result: %s", result[: 200] + "..." if len(result) > 200 else result
            )

            # Test 4: Get company policies
            logger.info("📊 Test 4: Get procurement policies")
            result = await provider.get_company_supplier_policy(policy_type="procurement")
            logger.info(
                "Result: %s", result[: 200] + "..." if len(result) > 200 else result
            )

            logger.info("✅ Supplier query tests completed!")

    except Exception as e:
        logger.error("❌ Error during testing: %s", e)
        raise


if __name__ == "__main__":
    asyncio.run(main())

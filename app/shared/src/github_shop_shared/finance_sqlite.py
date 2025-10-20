#!/usr/bin/env python3
"""
Finance Database Access Provider for Zava Retail - SQLite Edition

This module provides pre-written SQL queries for finance-related operations
to support the Finance Agent MCP server using SQLite with SQLAlchemy ORM.
"""

import asyncio
import json
import logging
from typing import Optional

from sqlalchemy import select, func, case, and_
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine, async_sessionmaker

from .config import Config
from .models.sqlite import (
    CompanyPolicy,
    Supplier,
    SupplierContract,
    Order,
    OrderItem,
    Store,
    Product,
    Category,
    ProductType,
    Inventory,
)

logger = logging.getLogger(__name__)
config = Config()


class FinanceSQLiteProvider:
    """Provides SQLite database access for finance-related operations."""

    def __init__(self, sqlite_url: Optional[str] = None) -> None:
        # Use default SQLite URL if not provided
        self.sqlite_url = sqlite_url or "sqlite+aiosqlite:////workspace/data/retail.db"
        self.engine: Optional[AsyncEngine] = None
        self.async_session_factory: Optional[async_sessionmaker] = None

    async def __aenter__(self) -> "FinanceSQLiteProvider":
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

                logger.info("✅ Finance SQLite async engine created")
            except Exception as e:
                logger.error("❌ Failed to create SQLAlchemy engine: %s", e)
                raise

    async def close_engine(self) -> None:
        """Close async engine and cleanup."""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.async_session_factory = None
            logger.info("✅ Finance SQLite async engine closed")

    def get_session(self) -> AsyncSession:
        """Get a new async session."""
        if not self.async_session_factory:
            raise RuntimeError(
                "No session factory available. Call create_pool() first."
            )
        return self.async_session_factory()

    async def get_company_order_policy(
        self, department: Optional[str] = None
    ) -> str:
        """
        Get company order processing policies.

        Returns company policies related to order processing,
        budget authorization, and related procedures.
        """
        async with self.get_session() as session:
            try:
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
                    return json.dumps(
                        {"c": [], "r": [], "n": 0, "msg": "No order policies found"},
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
                        "err": f"Company order policy query failed: {e!s}",
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
                from datetime import datetime, timedelta

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

    async def get_historical_sales_data(
        self,
        days_back: int = 90,
        store_id: Optional[int] = None,
        category_name: Optional[str] = None,
    ) -> str:
        """
        Get historical sales data with comprehensive metrics.

        Returns weekly aggregated sales statistics including total revenue, order counts,
        average values, and breakdowns by week, store, and category.
        Default lookback period is 90 days.
        """
        async with self.get_session() as session:
            try:
                from datetime import datetime, timedelta

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

                if not rows:
                    return json.dumps(
                        {
                            "c": [],
                            "r": [],
                            "n": 0,
                            "msg": f"No sales data found for last {days_back} days",
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
                        "err": f"Historical sales query failed: {e!s}",
                        "c": [],
                        "r": [],
                        "n": 0,
                    },
                    separators=(",", ":"),
                    default=str,
                )

    async def get_current_inventory_status(
        self,
        store_id: Optional[int] = None,
        category_name: Optional[str] = None,
        low_stock_threshold: int = 10,
    ) -> str:
        """
        Get current inventory status across stores.

        Returns inventory levels, values, and low stock alerts
        for products across all stores or filtered by specific criteria.
        """
        async with self.get_session() as session:
            try:
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

                if not rows:
                    return json.dumps(
                        {
                            "c": [],
                            "r": [],
                            "n": 0,
                            "msg": "No inventory data found",
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
                        "err": f"Inventory status query failed: {e!s}",
                        "c": [],
                        "r": [],
                        "n": 0,
                    },
                    separators=(",", ":"),
                    default=str,
                )

    async def get_stores(
        self,
        store_name: Optional[str] = None,
    ) -> str:
        """
        Get store information with optional filtering.

        Returns store details including store IDs, names, and online status.
        Can be filtered by store name. Returns all stores if no filters provided.

        Args:
            store_name: Optional store name to search for (partial match, case-insensitive)

        Returns:
            JSON string with format: {"c": [columns], "r": [[row data]], "n": count}
            Includes store_id, store_name, is_online, and rls_user_id.
        """
        async with self.get_session() as session:
            try:
                # Build query using ORM
                stmt = select(
                    Store.store_id,
                    Store.store_name,
                    Store.is_online,
                    Store.rls_user_id,
                )

                # Apply filter if provided
                if store_name:
                    stmt = stmt.where(
                        func.upper(Store.store_name).like(f"%{store_name.upper()}%")
                    )

                stmt = stmt.order_by(Store.store_name)

                result = await session.execute(stmt)
                rows = result.mappings().all()

                if not rows:
                    return json.dumps(
                        {
                            "c": [],
                            "r": [],
                            "n": 0,
                            "msg": "No stores found matching the criteria",
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
                        "err": f"Store query failed: {e!s}",
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
        provider = FinanceSQLiteProvider()
        await provider.create_pool()
        await provider.close_engine()
        return True
    except Exception as e:
        logger.error("Connection test failed: %s", e)
        return False


async def main() -> None:
    """Main function to test the finance provider."""
    logger.info("🤖 Finance SQLite Provider Test")
    logger.info("=" * 50)

    if not await test_connection():
        logger.error("❌ Error: Cannot connect to SQLite database")
        return

    try:
        async with FinanceSQLiteProvider() as provider:
            await provider.create_pool()

            logger.info("🧪 Testing Finance Queries:")
            logger.info("=" * 50)

            # Test 1: Get company order policies
            logger.info("📊 Test 1: Get company order policies")
            result = await provider.get_company_order_policy()
            logger.info(
                "Result: %s", result[: 200] + "..." if len(result) > 200 else result
            )

            # Test 2: Get supplier contract (assuming supplier_id 1 exists)
            logger.info("📊 Test 2: Get supplier contract")
            result = await provider.get_supplier_contract(supplier_id=1)
            logger.info(
                "Result: %s", result[: 200] + "..." if len(result) > 200 else result
            )

            # Test 3: Get historical sales data
            logger.info("📊 Test 3: Get historical sales data (90 days)")
            result = await provider.get_historical_sales_data(days_back=90)
            logger.info(
                "Result: %s", result[: 200] + "..." if len(result) > 200 else result
            )

            # Test 4: Get current inventory status
            logger.info("📊 Test 4: Get current inventory status")
            result = await provider.get_current_inventory_status(low_stock_threshold=10)
            logger.info(
                "Result: %s", result[: 200] + "..." if len(result) > 200 else result
            )

            # Test 5: Get all stores
            logger.info("📊 Test 5: Get all stores")
            result = await provider.get_stores()
            logger.info(
                "Result: %s", result[: 200] + "..." if len(result) > 200 else result
            )

            # Test 6: Get stores by name
            logger.info("📊 Test 6: Get stores by name (Online)")
            result = await provider.get_stores(store_name="Online")
            logger.info(
                "Result: %s", result[: 200] + "..." if len(result) > 200 else result
            )

            logger.info("✅ Finance query tests completed!")

    except Exception as e:
        logger.error("❌ Error during testing: %s", e)
        raise


if __name__ == "__main__":
    asyncio.run(main())

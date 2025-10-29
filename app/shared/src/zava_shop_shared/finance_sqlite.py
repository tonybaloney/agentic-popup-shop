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
        self.sqlite_url = sqlite_url or "sqlite+aiosqlite:////workspace/app/data/retail.db"
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

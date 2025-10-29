"""
Pytest configuration and fixtures for MCP server testing.

This module provides shared fixtures and configuration for all MCP server tests.
"""

import sys
import pytest
import asyncio
from typing import AsyncGenerator
from pathlib import Path
import tempfile
import os

# Add src to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from zava_shop_shared.finance_sqlite import FinanceSQLiteProvider
from zava_shop_shared.models.sqlite import Base


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for the test session.
    
    This fixture provides a single event loop for all async tests in the session.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db() -> AsyncGenerator:
    """
    Create a temporary test database with SQLite.

    This fixture:
    - Creates a temporary database file
    - Initializes all tables
    - Cleans up after the test

    Yields:
        FinanceSQLiteProvider: Initialized database provider
    """
    # Create temporary database file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        db_path = f.name

    db = None
    try:
        # Create provider pointing to temp database
        db = FinanceSQLiteProvider(sqlite_url=f"sqlite+aiosqlite:///{db_path}")
        await db.create_pool()

        # Create all tables using engine
        async with db.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield db

    finally:
        # Cleanup
        if db:
            await db.close_engine()
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.fixture
async def test_db_session(test_db: FinanceSQLiteProvider):
    """
    Create a test database session.

    This fixture provides an active session for database operations during tests.

    Args:
        test_db: The test database fixture

    Yields:
        AsyncSession: An active database session
    """
    session = test_db.get_session()
    try:
        yield session
    finally:
        await session.close()
@pytest.fixture
def sample_company_policies():
    """
    Provide sample company policy data for tests.
    
    Returns:
        dict: Sample company policy records with various configurations
    """
    return {
        "standard": {
            "name": "Standard Policy",
            "department": "General",
            "max_order_amount": 10000.00,
            "max_order_items": 100,
            "requires_approval": True,
            "approval_limit": 5000.00,
            "requires_po": True,
            "po_prefix": "PO",
            "lead_time_days": 5,
            "discount_percentage": 5.0,
        },
        "executive": {
            "name": "Executive Policy",
            "department": "Executive",
            "max_order_amount": 50000.00,
            "max_order_items": 500,
            "requires_approval": False,
            "approval_limit": 0.00,
            "requires_po": True,
            "po_prefix": "EXEPO",
            "lead_time_days": 2,
            "discount_percentage": 15.0,
        },
        "limited": {
            "name": "Limited Policy",
            "department": "Guest",
            "max_order_amount": 1000.00,
            "max_order_items": 10,
            "requires_approval": True,
            "approval_limit": 500.00,
            "requires_po": False,
            "po_prefix": None,
            "lead_time_days": 7,
            "discount_percentage": 0.0,
        },
    }


@pytest.fixture
def sample_suppliers():
    """
    Provide sample supplier data for tests.
    
    Returns:
        dict: Sample supplier records
    """
    return {
        "reliable": {
            "name": "Reliable Supplies Inc",
            "contact_email": "contact@reliable.com",
            "contact_phone": "555-0100",
            "address": "123 Business St",
            "city": "Business City",
            "state": "CA",
            "zip_code": "90210",
            "rating": 4.8,
            "is_active": True,
        },
        "standard": {
            "name": "Standard Goods Ltd",
            "contact_email": "orders@standardgoods.com",
            "contact_phone": "555-0200",
            "address": "456 Trade Ave",
            "city": "Commerce Town",
            "state": "TX",
            "zip_code": "75001",
            "rating": 4.2,
            "is_active": True,
        },
        "inactive": {
            "name": "Former Supplier Corp",
            "contact_email": "info@former.com",
            "contact_phone": "555-0300",
            "address": "789 Old Road",
            "city": "Legacy City",
            "state": "NY",
            "zip_code": "10001",
            "rating": 3.5,
            "is_active": False,
        },
    }


@pytest.fixture
def sample_stores():
    """
    Provide sample store data for tests.
    
    Returns:
        dict: Sample store records
    """
    return {
        "flagship": {
            "store_id": 1,
            "store_name": "Flagship Store",
            "city": "New York",
            "state": "NY",
            "manager_name": "John Manager",
            "manager_email": "john@flagship.com",
        },
        "downtown": {
            "store_id": 2,
            "store_name": "Downtown Shop",
            "city": "Los Angeles",
            "state": "CA",
            "manager_name": "Jane Manager",
            "manager_email": "jane@downtown.com",
        },
        "mall": {
            "store_id": 3,
            "store_name": "Mall Outlet",
            "city": "Chicago",
            "state": "IL",
            "manager_name": "Bob Manager",
            "manager_email": "bob@mall.com",
        },
    }


@pytest.fixture
def mock_auth_headers():
    """
    Provide mock authorization headers.
    
    Returns:
        dict: Authorization headers with valid token
    """
    return {
        "Authorization": "Bearer lets-go-seahawks",
        "Content-Type": "application/json",
    }


def pytest_configure(config):
    """
    Configure pytest with custom markers.
    
    Args:
        config: Pytest configuration object
    """
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )

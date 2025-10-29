"""
Integration tests for Supplier MCP Server tools.

Tests the actual MCP tool implementations for supplier management.
"""

import pytest

from zava_shop_mcp.supplier_server import (
    get_suppliers,
    get_supplier_details,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_suppliers(test_db):
    """Test retrieving all suppliers."""
    result = await get_suppliers()

    assert result is not None
    assert isinstance(result, (str, dict, list))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_supplier_details(test_db):
    """Test retrieving details for a specific supplier."""
    result = await get_supplier_details(supplier_id=1)

    assert result is not None
    assert isinstance(result, (str, dict, list))


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_supplier_details_nonexistent(test_db):
    """Test retrieving details for a non-existent supplier."""
    result = await get_supplier_details(supplier_id=99999)

    # Should handle gracefully - return empty or error
    assert result is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_db_can_query_suppliers(test_db_session):
    """Test that we can execute supplier queries on the test database."""
    from zava_shop_shared.models.sqlite import Supplier
    from sqlalchemy import select

    # Query all suppliers
    stmt = select(Supplier)
    result = await test_db_session.execute(stmt)
    suppliers = result.scalars().all()

    # Should return a list (possibly empty for fresh test DB)
    assert isinstance(suppliers, list)

"""
Integration tests for Finance MCP Server tools.

Tests the actual MCP tool implementations with a test database.
"""

import pytest

from zava_shop_mcp.finance_server import mcp

from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport

@pytest.fixture
async def main_mcp_client():
    async with Client(mcp) as client:
        yield client

@pytest.mark.parametrize(
    "department",
    [None, "Finance"]
)
async def test_get_company_order_policy(
    department: str | None,
    main_mcp_client: Client[FastMCPTransport],
):
    result = await main_mcp_client.call_tool(
        name="get_company_order_policy", arguments={"department": department}
    )
    assert result.data is not None


async def test_get_supplier_contract(
    main_mcp_client: Client[FastMCPTransport],
):
    result = await main_mcp_client.call_tool(
        name="get_supplier_contract", arguments={"supplier_id": 1}
    )
    assert result.data is not None

async def test_get_historical_sales_data(
    main_mcp_client: Client[FastMCPTransport],
):
    result = await main_mcp_client.call_tool(
        name="get_historical_sales_data", arguments={"days_back": 5, "store_id": 1, "category_name": "Footwear"}
    )
    assert result.data is not None

async def test_get_current_inventory_status(
    main_mcp_client: Client[FastMCPTransport],
):
    result = await main_mcp_client.call_tool(
        name="get_current_inventory_status", arguments={"store_id": 1, "category_name": "Footwear"}
    )
    assert result.data is not None

@pytest.mark.parametrize(
    "store_id",
    [None, "NYC"]
)
async def test_get_stores(
    store_id: str | None,
    main_mcp_client: Client[FastMCPTransport],
):
    result = await main_mcp_client.call_tool(
        name="get_stores", arguments={"store_name": store_id}
    )
    assert result.data is not None

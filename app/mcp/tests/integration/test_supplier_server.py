"""
Integration tests for Finance MCP Server tools.

Tests the actual MCP tool implementations with a test database.
"""

import pytest

from zava_shop_mcp.supplier_server import mcp

from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport

@pytest.fixture
async def main_mcp_client():
    async with Client(mcp) as client:
        yield client


async def test_find_suppliers_for_request(
    main_mcp_client: Client[FastMCPTransport],
):
    result = await main_mcp_client.call_tool(
        name="find_suppliers_for_request", arguments={}
    )
    assert result.data is not None


async def test_get_supplier_history_and_performance(
    main_mcp_client: Client[FastMCPTransport],
):
    result = await main_mcp_client.call_tool(
        name="get_supplier_history_and_performance", arguments={"supplier_id": 1, "months_back": 6}
    )
    assert result.data is not None


async def test_get_supplier_contracts(
    main_mcp_client: Client[FastMCPTransport],
):
    result = await main_mcp_client.call_tool(
        name="get_supplier_contract", arguments={"supplier_id": 1}
    )
    assert result.data is not None

async def test_get_supplier_policies(
    main_mcp_client: Client[FastMCPTransport],
):
    result = await main_mcp_client.call_tool(
        name="get_company_supplier_policy", arguments={"policy_type": "procurement", "department": "Finance"}
    )
    assert result.data is not None

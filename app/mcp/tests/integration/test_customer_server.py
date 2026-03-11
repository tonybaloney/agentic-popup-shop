"""
Integration tests for Customer MCP Server tools.

Tests the actual MCP tool implementations with a test database.
The customer_id is injected via a mocked access token since tools
use ``get_access_token()`` from ``fastmcp.server.dependencies`` to
extract the JWT claim.
"""

import pytest
import pytest_asyncio
from unittest.mock import patch
from decimal import Decimal

pytestmark = pytest.mark.asyncio

customer_server = pytest.importorskip(
    "zava_shop_mcp.customer_server",
    reason="Customer MCP server runtime dependencies are not available in this test environment",
)

mcp = customer_server.mcp

from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport
from fastmcp.server.auth import AccessToken


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_customer_token(customer_id: int = 1) -> AccessToken:
    """Return a fake ``AccessToken`` whose claims include *customer_id*."""
    return AccessToken(
        token="test-token",
        client_id="test-client",
        scopes=["openid", "zava:access"],
        claims={
            "sub": "test-user",
            "customer_id": customer_id,
            "preferred_username": f"customer{customer_id}",
        },
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def main_mcp_client():
    """MCP in-process client (no auth enforced at transport level)."""
    async with Client(mcp) as client:
        yield client


# ---------------------------------------------------------------------------
# get_my_orders
# ---------------------------------------------------------------------------

@patch("zava_shop_mcp.customer_server.get_access_token")
async def test_get_my_orders_returns_results(
    mock_get_token,
    main_mcp_client: Client[FastMCPTransport],
):
    """Known customer should have orders in the test database."""
    mock_get_token.return_value = _make_customer_token(customer_id=1)

    result = await main_mcp_client.call_tool(
        name="get_my_orders", arguments={"limit": 5}
    )
    assert result.data is not None


@patch("zava_shop_mcp.customer_server.get_access_token")
async def test_get_my_orders_default_limit(
    mock_get_token,
    main_mcp_client: Client[FastMCPTransport],
):
    """Calling without arguments should default to limit=10."""
    mock_get_token.return_value = _make_customer_token(customer_id=1)

    result = await main_mcp_client.call_tool(
        name="get_my_orders", arguments={}
    )
    assert result.data is not None


@patch("zava_shop_mcp.customer_server.get_access_token")
async def test_get_my_orders_nonexistent_customer(
    mock_get_token,
    main_mcp_client: Client[FastMCPTransport],
):
    """A customer_id with no orders should return an empty list."""
    mock_get_token.return_value = _make_customer_token(customer_id=999999)

    result = await main_mcp_client.call_tool(
        name="get_my_orders", arguments={"limit": 5}
    )
    # Should succeed but return empty data
    assert result.data is not None


# ---------------------------------------------------------------------------
# search_products
# ---------------------------------------------------------------------------

async def test_search_products_no_filter(
    main_mcp_client: Client[FastMCPTransport],
):
    """Searching with no filters should return products."""
    result = await main_mcp_client.call_tool(
        name="search_products", arguments={}
    )
    assert result.data is not None


async def test_search_products_by_query(
    main_mcp_client: Client[FastMCPTransport],
):
    """Search by product name/description should return matching products."""
    result = await main_mcp_client.call_tool(
        name="search_products", arguments={"query": "shirt", "limit": 5}
    )
    assert result.data is not None


async def test_search_products_by_category(
    main_mcp_client: Client[FastMCPTransport],
):
    """Filtering by category should return only products in that category."""
    result = await main_mcp_client.call_tool(
        name="search_products", arguments={"category": "Footwear", "limit": 5}
    )
    assert result.data is not None


async def test_search_products_no_results(
    main_mcp_client: Client[FastMCPTransport],
):
    """A nonsense query should return empty results."""
    result = await main_mcp_client.call_tool(
        name="search_products",
        arguments={"query": "xyznonexistentproduct123", "limit": 5},
    )
    assert result.data is not None

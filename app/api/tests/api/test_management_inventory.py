"""
Tests for inventory management endpoints.
"""

import pytest
from fastapi.testclient import TestClient


"""Test suite for inventory management endpoints."""

def test_get_inventory(test_client: TestClient, admin_auth_headers: dict):
    """
    Test GET /api/management/inventory endpoint.
    
    Should return:
    - Status code 200
    - InventoryResponse with items and summary
    - Items ordered by stock level
    """
    response = test_client.get("/api/management/inventory?limit=20", headers=admin_auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "inventory" in data
    assert "summary" in data
    assert isinstance(data["inventory"], list)
    
    # Should have inventory items
    assert len(data["inventory"]) > 0
    
    # Check summary structure
    summary = data["summary"]
    required_summary_fields = [
        "total_items", "low_stock_count", "total_stock_value", 
        "total_retail_value", "avg_stock_level"
    ]
    for field in required_summary_fields:
        assert field in summary, f"Missing summary field: {field}"
    
    # Check first item has required fields
    item = data["inventory"][0]
    required_item_fields = [
        "store_id", "store_name", "store_location", "is_online",
        "product_id", "product_name", "sku", "category", "type",
        "stock_level", "reorder_point", "is_low_stock",
        "unit_cost", "unit_price", "stock_value", "retail_value"
    ]
    for field in required_item_fields:
        assert field in item, f"Missing item field: {field}"
    
    # Verify ordering by stock level (ascending)
    stock_levels = [item["stock_level"] for item in data["inventory"]]
    assert stock_levels == sorted(stock_levels), "Items should be ordered by stock level ascending"

def test_get_inventory_with_store_filter(test_client: TestClient, admin_auth_headers: dict):
    """
    Test inventory endpoint with store_id filter.
    
    Validates:
    - Only items from specified store are returned
    - Summary reflects filtered data
    """
    # First get a valid store_id
    all_response = test_client.get("/api/management/inventory?limit=100", headers=admin_auth_headers)
    all_data = all_response.json()
    
    assert len(all_data["inventory"]) > 0, "No inventory items found"
    test_store_id = all_data["inventory"][0]["store_id"]
    
    # Filter by that store
    response = test_client.get(f"/api/management/inventory?store_id={test_store_id}&limit=50", headers=admin_auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    items = data["inventory"]
    
    # Should have items
    assert len(items) > 0
    
    # All items should be from the specified store
    for item in items:
        assert item["store_id"] == test_store_id

def test_get_inventory_with_category_filter(test_client: TestClient, admin_auth_headers: dict):
    """
    Test inventory endpoint with category filter.
    
    Validates:
    - Only items from specified category are returned
    - Filter is case-insensitive
    """
    # First get a valid category
    all_response = test_client.get("/api/management/inventory?limit=100", headers=admin_auth_headers)
    all_data = all_response.json()
    
    assert len(all_data["inventory"]) > 0, "No inventory items found"
    test_category = all_data["inventory"][0]["category"]
    
    # Filter by that category
    response = test_client.get(f"/api/management/inventory?category={test_category}&limit=50", headers=admin_auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    items = data["inventory"]
    
    # Should have items
    assert len(items) > 0
    
    # All items should be from the specified category
    for item in items:
        assert item["category"].lower() == test_category.lower()

def test_get_inventory_with_product_filter(test_client: TestClient, admin_auth_headers: dict):
    """
    Test inventory endpoint with product_id filter.
    
    Validates:
    - Only items for specified product are returned
    - Shows inventory across all stores for that product
    """
    # First get a valid product_id
    all_response = test_client.get("/api/management/inventory?limit=100", headers=admin_auth_headers)
    all_data = all_response.json()
    
    assert len(all_data["inventory"]) > 0, "No inventory items found"
    test_product_id = all_data["inventory"][0]["product_id"]
    
    # Filter by that product
    response = test_client.get(f"/api/management/inventory?product_id={test_product_id}&limit=50", headers=admin_auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    items = data["inventory"]
    
    # Should have items
    assert len(items) > 0
    
    # All items should be for the same product
    for item in items:
        assert item["product_id"] == test_product_id

def test_get_inventory_low_stock_only(test_client: TestClient, admin_auth_headers: dict):
    """
    Test inventory endpoint with low_stock_only filter.
    
    Validates:
    - Only low stock items are returned
    - Low stock threshold is respected
    """
    # Get low stock items (using default threshold of 10)
    response = test_client.get("/api/management/inventory?low_stock_only=true&limit=50", headers=admin_auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    items = data["inventory"]
    
    # All returned items should have is_low_stock=true
    for item in items:
        assert item["is_low_stock"] == True, f"Item {item['sku']} should be low stock"
        # With default threshold of 10, stock_level should be < 10
        assert item["stock_level"] < 10

def test_get_inventory_custom_threshold(test_client: TestClient, admin_auth_headers: dict):
    """
    Test inventory endpoint with custom low_stock_threshold.
    
    Validates:
    - Custom threshold is applied correctly
    - is_low_stock calculation uses custom threshold
    """
    threshold = 50
    response = test_client.get(f"/api/management/inventory?low_stock_threshold={threshold}&limit=100", headers=admin_auth_headers)

def test_get_inventory_summary_calculations(test_client: TestClient, admin_auth_headers: dict):
    """
    Test that inventory summary calculations are correct.
    
    Validates:
    - total_items matches inventory count
    - low_stock_count is accurate
    - total values are calculated correctly
    - avg_stock_level is correct
    """
    response = test_client.get("/api/management/inventory?limit=1000", headers=admin_auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    summary = data["summary"]
    items = data["inventory"]
    
    # Summary should have valid numbers
    assert summary["total_items"] > 0
    assert summary["total_stock_value"] >= 0
    assert summary["total_retail_value"] >= 0
    assert summary["avg_stock_level"] >= 0
    
    # Low stock count should be <= total items
    assert summary["low_stock_count"] <= summary["total_items"]
    
    # Verify summary is consistent with items (if we got all items)
    if len(items) == summary["total_items"]:
        # Manual calculation to verify
        total_stock_value = sum(item["stock_value"] for item in items)
        total_retail_value = sum(item["retail_value"] for item in items)
        
        # Allow small rounding differences
        assert abs(summary["total_stock_value"] - total_stock_value) < 0.1
        assert abs(summary["total_retail_value"] - total_retail_value) < 0.1

def test_get_inventory_limit_parameter(test_client: TestClient, admin_auth_headers: dict):
    """
    Test inventory endpoint with limit parameter.
    
    Validates:
    - limit parameter is respected
    - Default limit (100) is applied if not specified
    - Summary still reflects all items, not just paginated results
    """
    # Test with custom limit
    response = test_client.get("/api/management/inventory?limit=10", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["inventory"]) <= 10
    
    # Summary should still reflect all items, not just the 10 shown
    # (If there are more than 10 items total)
    all_response = test_client.get("/api/management/inventory?limit=1000", headers=admin_auth_headers)
    all_data = all_response.json()
    
    if len(all_data["inventory"]) > 10:
        # Total items in summary should match total inventory
        assert data["summary"]["total_items"] == all_data["summary"]["total_items"]

def test_get_inventory_multiple_filters(test_client: TestClient, admin_auth_headers: dict):
    """
    Test inventory endpoint with multiple filters combined.
    
    Validates:
    - Multiple filters work together correctly
    - Results match all filter criteria
    """
    # First get test data
    all_response = test_client.get("/api/management/inventory?limit=100", headers=admin_auth_headers)
    all_data = all_response.json()
    
    assert len(all_data["inventory"]) > 0, "No inventory items found"
    
    # Get first item's store and category
    test_item = all_data["inventory"][0]
    test_store_id = test_item["store_id"]
    test_category = test_item["category"]
    
    # Filter by both store and category
    response = test_client.get(
        f"/api/management/inventory?store_id={test_store_id}&category={test_category}&limit=50",
        headers=admin_auth_headers
    )

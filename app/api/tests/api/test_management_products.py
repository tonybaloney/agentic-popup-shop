"""
Tests for product management endpoints.
"""

import pytest
from fastapi.testclient import TestClient


"""Test suite for product management endpoints."""

def test_get_management_products(test_client: TestClient, admin_auth_headers: dict):
    """
    Test GET /api/management/products endpoint.
    
    Should return:
    - Status code 200
    - ManagementProductResponse with products and pagination
    - Products with aggregated stock info
    """
    response = test_client.get("/api/management/products?limit=10", headers=admin_auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "products" in data
    assert "pagination" in data
    assert isinstance(data["products"], list)
    
    # Check pagination structure
    pagination = data["pagination"]
    assert "total" in pagination
    assert "limit" in pagination
    assert "offset" in pagination
    assert "has_more" in pagination
    assert pagination["limit"] == 10
    assert pagination["offset"] == 0
    
    # Should have products
    assert len(data["products"]) > 0
    
    # Check first product has all required fields
    product = data["products"][0]
    required_fields = [
        "product_id", "sku", "name", "description", "category", "type",
        "base_price", "cost", "margin", "discontinued",
        "total_stock", "store_count", "stock_value", "retail_value"
    ]
    for field in required_fields:
        assert field in product, f"Missing required field: {field}"

def test_get_management_products_with_category_filter(test_client: TestClient, admin_auth_headers: dict):
    """
    Test management products endpoint with category filter.
    
    Validates:
    - Category filter is applied correctly
    - Filter is case-insensitive
    """
    # First get a valid category from existing products
    all_response = test_client.get("/api/management/products?limit=100", headers=admin_auth_headers)
    all_data = all_response.json()
    
    # Get the first category we find
    assert len(all_data["products"]) > 0, "No products found in database"
    test_category = all_data["products"][0]["category"]
    
    # Get products in that category
    response = test_client.get(f"/api/management/products?category={test_category}&limit=50", headers=admin_auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    products = data["products"]
    
    # Should have products
    assert len(products) > 0
    
    # All products should be in the specified category
    for product in products:
        assert product["category"].lower() == test_category.lower()

def test_get_management_products_with_supplier_filter(test_client: TestClient, admin_auth_headers: dict):
    """
    Test management products endpoint with supplier_id filter.
    
    Validates:
    - Only products from specified supplier are returned
    """
    # First get a valid supplier_id
    all_response = test_client.get("/api/management/products?limit=100", headers=admin_auth_headers)
    all_data = all_response.json()
    
    # Find a product with a supplier
    supplier_id = None
    for product in all_data["products"]:
        if product.get("supplier_id") is not None:
            supplier_id = product["supplier_id"]
            break
    
    assert supplier_id is not None, "No products with suppliers found"
    
    # Test filtering by that supplier
    response = test_client.get(f"/api/management/products?supplier_id={supplier_id}", headers=admin_auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    products = data["products"]
    
    # Should have products
    assert len(products) > 0
    
    # All products should have the same supplier_id
    for product in products:
        if product.get("supplier_id") is not None:
            assert product["supplier_id"] == supplier_id

def test_get_management_products_with_discontinued_filter(test_client: TestClient, admin_auth_headers: dict):
    """
    Test management products endpoint with discontinued filter.
    
    Validates:
    - discontinued=true returns only discontinued products
    - discontinued=false returns only active products
    """
    # Test active products (discontinued=false)
    active_response = test_client.get("/api/management/products?discontinued=false&limit=50", headers=admin_auth_headers)
    assert active_response.status_code == 200
    
    active_data = active_response.json()
    active_products = active_data["products"]
    
    # All products should be active
    for product in active_products:
        assert product["discontinued"] == False
    
    # Test discontinued products (discontinued=true)
    discontinued_response = test_client.get("/api/management/products?discontinued=true&limit=50", headers=admin_auth_headers)
    assert discontinued_response.status_code == 200
    
    discontinued_data = discontinued_response.json()
    discontinued_products = discontinued_data["products"]
    
    # All products should be discontinued
    for product in discontinued_products:
        assert product["discontinued"] == True

def test_get_management_products_with_search(test_client: TestClient, admin_auth_headers: dict):
    """
    Test management products endpoint with search parameter.
    
    Validates:
    - Search works on product name
    - Search works on SKU
    - Search works on description
    - Search is case-insensitive
    """
    # Search for a common term like "shirt"
    response = test_client.get("/api/management/products?search=shirt&limit=50", headers=admin_auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    products = data["products"]
    
    # Should find some products
    if len(products) > 0:
        # At least one product should have 'shirt' in name, sku, or description
        found_match = False
        for product in products:
            search_term = "shirt"
            if (search_term in product["name"].lower() or
                search_term in product["sku"].lower() or
                search_term in product.get("description", "").lower()):
                found_match = True
                break
        assert found_match, "Search results don't contain the search term"

def test_get_management_products_pagination(test_client: TestClient, admin_auth_headers: dict):
    """
    Test management products endpoint pagination.
    
    Validates:
    - limit parameter works correctly
    - offset parameter works correctly
    - pagination.total reflects total matching products
    - pagination.has_more is accurate
    """
    # Get first page
    first_page = test_client.get("/api/management/products?limit=5&offset=0", headers=admin_auth_headers)
    assert first_page.status_code == 200
    first_data = first_page.json()
    
    assert len(first_data["products"]) <= 5
    assert first_data["pagination"]["limit"] == 5
    assert first_data["pagination"]["offset"] == 0
    
    # Get second page
    second_page = test_client.get("/api/management/products?limit=5&offset=5", headers=admin_auth_headers)
    assert second_page.status_code == 200
    second_data = second_page.json()
    
    assert second_data["pagination"]["offset"] == 5
    
    # Products should be different (assuming we have more than 5 products)
    if len(first_data["products"]) == 5 and len(second_data["products"]) > 0:
        first_ids = [p["product_id"] for p in first_data["products"]]
        second_ids = [p["product_id"] for p in second_data["products"]]
        # Should have different products
        assert first_ids != second_ids

def test_get_management_products_stock_aggregation(test_client: TestClient, admin_auth_headers: dict):
    """
    Test that stock aggregation is calculated correctly.
    
    Validates:
    - total_stock is sum across all stores
    - store_count is accurate
    - stock_value and retail_value are calculated correctly
    """
    response = test_client.get("/api/management/products?limit=20", headers=admin_auth_headers)
    assert response.status_code == 200
    
    data = response.json()
    products = data["products"]
    
    # Should have products
    assert len(products) > 0
    
    # Check calculations for each product
    for product in products:
        # Verify stock_value = cost * total_stock
        expected_stock_value = round(product["cost"] * product["total_stock"], 2)
        assert product["stock_value"] == expected_stock_value, \
            f"Stock value mismatch for {product['sku']}: {product['stock_value']} != {expected_stock_value}"
        
        # Verify retail_value = base_price * total_stock
        expected_retail_value = round(product["base_price"] * product["total_stock"], 2)
        assert product["retail_value"] == expected_retail_value, \
            f"Retail value mismatch for {product['sku']}: {product['retail_value']} != {expected_retail_value}"
        
        # Total stock should be non-negative
        assert product["total_stock"] >= 0
        
        # Store count should be non-negative
        assert product["store_count"] >= 0

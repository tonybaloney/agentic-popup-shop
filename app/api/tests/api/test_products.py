"""
Tests for product-related endpoints.
"""

import pytest
from fastapi.testclient import TestClient


"""Test suite for product endpoints."""

def test_get_featured_products(test_client: TestClient):
    """
    Test GET /api/products/featured endpoint.
    
    Should return:
    - Status code 200
    - ProductList response model
    - Products ordered by margin and randomized
    """
    response = test_client.get("/api/products/featured")
    
    assert response.status_code == 200
    data = response.json()
    
    # Validate response structure
    assert "products" in data
    assert "total" in data
    assert isinstance(data["products"], list)
    assert isinstance(data["total"], int)
    
    # Default limit is 8
    assert len(data["products"]) <= 8
    assert data["total"] == len(data["products"])
    
    # Check products have required fields
    if len(data["products"]) > 0:
        product = data["products"][0]
        assert "product_id" in product
        assert "sku" in product
        assert "product_name" in product
        assert "category_name" in product
        assert "unit_price" in product

def test_get_featured_products_with_limit(test_client: TestClient):
    """
    Test featured products endpoint with limit parameter.
    
    Validates:
    - Limit parameter is respected
    - Default limit is 8
    - Max limit is 50
    """
    # Test with custom limit
    response = test_client.get("/api/products/featured?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data["products"]) <= 5
    
    # Test with minimum limit
    response = test_client.get("/api/products/featured?limit=1")
    assert response.status_code == 200
    data = response.json()
    assert len(data["products"]) <= 1
    
    # Test default limit (8)
    response = test_client.get("/api/products/featured")
    assert response.status_code == 200
    data = response.json()
    assert len(data["products"]) <= 8

def test_get_products_by_category(test_client: TestClient):
    """
    Test GET /api/products/category/{category} endpoint.
    
    Should return:
    - Status code 200
    - ProductList with products from specified category
    - Pagination support
    """
    # First get categories to find a valid one
    categories_response = test_client.get("/api/categories")
    assert categories_response.status_code == 200
    categories_data = categories_response.json()
    
    if len(categories_data["categories"]) > 0:
        category_name = categories_data["categories"][0]["name"]
        
        response = test_client.get(f"/api/products/category/{category_name}")
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert "products" in data
        assert "total" in data
        assert isinstance(data["products"], list)
        assert isinstance(data["total"], int)
        
        # All products should be from the requested category
        for product in data["products"]:
            assert product["category_name"].lower() == category_name.lower()
        
        # Test pagination
        if data["total"] > 10:
            response_page2 = test_client.get(f"/api/products/category/{category_name}?limit=10&offset=10")
            assert response_page2.status_code == 200

def test_get_products_by_category_invalid_category(test_client: TestClient):
    """
    Test category endpoint with non-existent category.
    
    Should return:
    - Status code 404
    - Error message indicating no products found
    """
    response = test_client.get("/api/products/category/NonExistentCategory123")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower() or "no products" in data["detail"].lower()

def test_get_product_by_id(test_client: TestClient):
    """
    Test GET /api/products/{product_id} endpoint.
    
    Should return:
    - Status code 200
    - Product response model
    - Correct product details
    """
    # First get featured products to get a valid product ID
    featured_response = test_client.get("/api/products/featured?limit=1")
    assert featured_response.status_code == 200
    featured_data = featured_response.json()
    
    if len(featured_data["products"]) > 0:
        product_id = featured_data["products"][0]["product_id"]
        
        response = test_client.get(f"/api/products/{product_id}")
        assert response.status_code == 200
        data = response.json()
        
        # Validate product fields
        assert data["product_id"] == product_id
        assert "sku" in data
        assert "product_name" in data
        assert "category_name" in data
        assert "type_name" in data
        assert "unit_price" in data
        assert "cost" in data
        assert "gross_margin_percent" in data
        assert "product_description" in data
        assert isinstance(data["unit_price"], (int, float))
        assert isinstance(data["cost"], (int, float))

def test_get_product_by_id_not_found(test_client: TestClient):
    """
    Test product by ID endpoint with non-existent ID.
    
    Should return:
    - Status code 404
    - Error message
    """
    response = test_client.get("/api/products/999999")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()

def test_get_product_by_sku(test_client: TestClient):
    """
    Test GET /api/products/sku/{sku} endpoint.
    
    Should return:
    - Status code 200
    - Product response model
    """
    # First get featured products to get a valid SKU
    featured_response = test_client.get("/api/products/featured?limit=1")
    assert featured_response.status_code == 200
    featured_data = featured_response.json()
    
    if len(featured_data["products"]) > 0:
        sku = featured_data["products"][0]["sku"]
        
        response = test_client.get(f"/api/products/sku/{sku}")
        assert response.status_code == 200
        data = response.json()
        
        # Validate product fields
        assert data["sku"] == sku
        assert "product_id" in data
        assert "product_name" in data
        assert "category_name" in data
        assert "type_name" in data
        assert "unit_price" in data
        assert isinstance(data["product_id"], int)
        assert isinstance(data["unit_price"], (int, float))

def test_get_product_by_sku_not_found(test_client: TestClient):
    """
    Test product by SKU endpoint with non-existent SKU.
    
    Should return:
    - Status code 404
    - Error message
    """
    response = test_client.get("/api/products/sku/INVALID-SKU-12345")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()

"""
Tests for management dashboard endpoints.
"""

import pytest
from fastapi.testclient import TestClient


"""Test suite for management dashboard endpoints."""

def test_get_top_categories(test_client: TestClient, admin_auth_headers: dict):
    """
    Test GET /api/management/dashboard/top-categories endpoint.
    
    Should return:
    - Status code 200
    - TopCategoryList response model
    - Categories ordered by revenue
    """
    response = test_client.get("/api/management/dashboard/top-categories", headers=admin_auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Validate response structure
    assert "categories" in data
    assert "total" in data
    assert "max_value" in data
    assert isinstance(data["categories"], list)
    assert isinstance(data["total"], int)
    assert isinstance(data["max_value"], (int, float))
    
    # Default limit is 5
    assert len(data["categories"]) <= 5
    assert data["total"] == len(data["categories"])
    
    # Check categories have required fields
    if len(data["categories"]) > 0:
        category = data["categories"][0]
        assert "name" in category
        assert "revenue" in category
        assert "percentage" in category
        assert "product_count" in category
        assert "total_stock" in category
        assert "cost_value" in category
        assert "potential_profit" in category
        
        # Verify ordering (by revenue descending)
        if len(data["categories"]) > 1:
            for i in range(len(data["categories"]) - 1):
                assert data["categories"][i]["revenue"] >= data["categories"][i + 1]["revenue"]

def test_get_top_categories_with_limit(test_client: TestClient, admin_auth_headers: dict):
    """
    Test top categories endpoint with limit parameter.
    
    Validates:
    - Limit parameter is respected
    - Default limit is 5
    - Max limit is 10
    """
    # Test with custom limit
    response = test_client.get("/api/management/dashboard/top-categories?limit=3", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["categories"]) <= 3
    
    # Test with max limit
    response = test_client.get("/api/management/dashboard/top-categories?limit=10", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["categories"]) <= 10
    
    # Test default limit (5)
    response = test_client.get("/api/management/dashboard/top-categories", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["categories"]) <= 5

def test_get_top_categories_calculations(test_client: TestClient, admin_auth_headers: dict):
    """
    Test that top categories calculations are correct.
    
    Validates:
    - Revenue percentages are calculated correctly
    - Max value matches top category
    - Potential profit is calculated correctly
    """
    response = test_client.get("/api/management/dashboard/top-categories?limit=5", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    
    if len(data["categories"]) > 0:
        # Max value should match the top category's revenue
        top_category = data["categories"][0]
        assert data["max_value"] == top_category["revenue"]
        
        # Top category should have 100% percentage
        assert top_category["percentage"] == 100.0
        
        # Potential profit should be revenue - cost_value
        expected_profit = round(top_category["revenue"] - top_category["cost_value"], 2)
        assert abs(top_category["potential_profit"] - expected_profit) < 0.01
        
        # All percentages should be relative to max_value
        for category in data["categories"]:
            expected_percentage = round((category["revenue"] / data["max_value"]) * 100, 1)
            assert abs(category["percentage"] - expected_percentage) < 0.1

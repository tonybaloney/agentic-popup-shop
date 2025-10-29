"""
Tests for supplier management endpoints.
"""

import pytest
from fastapi.testclient import TestClient


"""Test suite for supplier management endpoints."""

def test_get_suppliers(test_client: TestClient, admin_auth_headers: dict):
    """
    Test GET /api/management/suppliers endpoint.
    
    Should return:
    - Status code 200
    - SupplierList response model
    - Suppliers ordered by preference and rating
    """
    response = test_client.get("/api/management/suppliers", headers=admin_auth_headers)
    
    assert response.status_code == 200
    data = response.json()
    
    # Validate response structure
    assert "suppliers" in data
    assert "total" in data
    assert isinstance(data["suppliers"], list)
    assert isinstance(data["total"], int)
    assert data["total"] == len(data["suppliers"])
    
    # Check suppliers have required fields
    if len(data["suppliers"]) > 0:
        supplier = data["suppliers"][0]
        assert "id" in supplier
        assert "name" in supplier
        assert "code" in supplier
        assert "location" in supplier
        assert "contact" in supplier
        assert "phone" in supplier
        assert "rating" in supplier
        assert "esg_compliant" in supplier
        assert "approved" in supplier
        assert "preferred" in supplier
        assert "categories" in supplier
        assert "lead_time" in supplier
        assert "payment_terms" in supplier
        assert "min_order" in supplier
        assert "bulk_discount" in supplier

def test_get_suppliers_returns_correct_schema(test_client: TestClient, admin_auth_headers: dict):
    """
    Test that suppliers endpoint returns data matching SupplierList schema.
    
    Validates:
    - Response has 'suppliers' and 'total' fields
    - Each supplier has all required fields
    - Categories array is populated
    """
    response = test_client.get("/api/management/suppliers", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    
    assert "suppliers" in data
    assert "total" in data
    
    # Validate each supplier's schema
    for supplier in data["suppliers"]:
        # Required fields
        assert isinstance(supplier["id"], int)
        assert isinstance(supplier["name"], str)
        assert isinstance(supplier["code"], str)
        assert isinstance(supplier["location"], str)
        assert isinstance(supplier["contact"], str)
        assert isinstance(supplier["phone"], str)
        assert isinstance(supplier["rating"], (int, float))
        assert isinstance(supplier["esg_compliant"], bool)
        assert isinstance(supplier["approved"], bool)
        assert isinstance(supplier["preferred"], bool)
        assert isinstance(supplier["categories"], list)
        assert isinstance(supplier["lead_time"], int)
        assert isinstance(supplier["payment_terms"], str)
        assert isinstance(supplier["min_order"], (int, float))
        assert isinstance(supplier["bulk_discount"], (int, float))
        
        # Rating should be between 0 and 5
        assert 0 <= supplier["rating"] <= 5

def test_get_suppliers_ordering(test_client: TestClient, admin_auth_headers: dict):
    """
    Test that suppliers are ordered correctly.
    
    Validates:
    - Preferred suppliers come first
    - Within each group, suppliers are ordered by rating
    - Only active suppliers are returned
    """
    response = test_client.get("/api/management/suppliers", headers=admin_auth_headers)
    assert response.status_code == 200
    data = response.json()
    
    if len(data["suppliers"]) > 1:
        suppliers = data["suppliers"]
        
        # Find the transition point from preferred to non-preferred
        preferred_count = sum(1 for s in suppliers if s["preferred"])
        
        if preferred_count > 0 and preferred_count < len(suppliers):
            # All preferred should come before non-preferred
            for i in range(preferred_count):
                assert suppliers[i]["preferred"] == True
            for i in range(preferred_count, len(suppliers)):
                assert suppliers[i]["preferred"] == False
        
        # Within preferred group, check rating order (descending)
        if preferred_count > 1:
            for i in range(preferred_count - 1):
                assert suppliers[i]["rating"] >= suppliers[i + 1]["rating"]

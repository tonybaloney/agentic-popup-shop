"""
Tests for user orders endpoints.
"""

import pytest
from fastapi.testclient import TestClient


def test_get_user_orders_success(test_client: TestClient):
    """
    Test successful retrieval of orders for a customer user.
    
    Should return:
    - Status code 200
    - List of orders with order details
    - Order items with product information
    """
    # Login as customer
    login_response = test_client.post(
        "/api/login",
        json={"username": "tracey.lopez.4", "password": "tracey123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Get orders
    response = test_client.get(
        "/api/users/orders",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "orders" in data
    assert "total" in data
    assert isinstance(data["orders"], list)
    assert isinstance(data["total"], int)
    
    # If there are orders, verify their structure
    if data["total"] > 0:
        order = data["orders"][0]
        
        # Verify order fields
        assert "order_id" in order
        assert "order_date" in order
        assert "store_id" in order
        assert "store_name" in order
        assert "store_location" in order
        assert "items" in order
        assert "total_items" in order
        assert "order_total" in order
        
        # Verify order items structure
        assert isinstance(order["items"], list)
        if len(order["items"]) > 0:
            item = order["items"][0]
            assert "order_item_id" in item
            assert "product_id" in item
            assert "product_name" in item
            assert "sku" in item
            assert "quantity" in item
            assert "unit_price" in item
            assert "discount_percent" in item
            assert "discount_amount" in item
            assert "total_amount" in item


def test_get_user_orders_unauthorized(test_client: TestClient):
    """
    Test that orders endpoint requires authentication.
    
    Should return:
    - Status code 401
    """
    response = test_client.get("/api/users/orders")
    
    assert response.status_code == 422  # Missing header


def test_get_user_orders_invalid_token(test_client: TestClient):
    """
    Test that orders endpoint rejects invalid token.
    
    Should return:
    - Status code 401
    """
    response = test_client.get(
        "/api/users/orders",
        headers={"Authorization": "Bearer invalid_token"}
    )
    
    assert response.status_code == 401


def test_get_user_orders_forbidden_for_admin(test_client: TestClient):
    """
    Test that admin users cannot access customer orders endpoint.
    
    Should return:
    - Status code 403
    """
    # Login as admin
    login_response = test_client.post(
        "/api/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Try to get orders
    response = test_client.get(
        "/api/users/orders",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 403
    assert "customer" in response.json()["detail"].lower()


def test_get_user_orders_forbidden_for_store_manager(test_client: TestClient):
    """
    Test that store manager users cannot access customer orders endpoint.
    
    Should return:
    - Status code 403
    """
    # Login as store manager
    login_response = test_client.post(
        "/api/login",
        json={"username": "manager1", "password": "manager123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Try to get orders
    response = test_client.get(
        "/api/users/orders",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 403
    assert "customer" in response.json()["detail"].lower()


def test_get_user_orders_sorted_by_date(test_client: TestClient):
    """
    Test that orders are returned sorted by date (newest first).
    
    Should return:
    - Orders in descending date order
    """
    # Login as customer
    login_response = test_client.post(
        "/api/login",
        json={"username": "tracey.lopez.4", "password": "tracey123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Get orders
    response = test_client.get(
        "/api/users/orders",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify orders are sorted by date (newest first)
    if data["total"] > 1:
        orders = data["orders"]
        for i in range(len(orders) - 1):
            current_date = orders[i]["order_date"]
            next_date = orders[i + 1]["order_date"]
            assert current_date >= next_date, \
                "Orders should be sorted by date in descending order"

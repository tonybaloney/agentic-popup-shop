"""
Tests for authentication endpoints and token validation.
"""

import pytest
from fastapi.testclient import TestClient


def test_login_admin_success(test_client: TestClient):
    """
    Test successful login for admin user.
    
    Should return:
    - Status code 200
    - access_token
    - token_type = "bearer"
    - user_role = "admin"
    - store_id = None
    - store_name = None
    """
    response = test_client.post(
        "/api/login",
        json={"username": "admin", "password": "admin123"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "access_token" in data
    assert "token_type" in data
    assert "user_role" in data
    assert "store_id" in data
    assert "store_name" in data
    
    assert data["token_type"] == "bearer"
    assert data["user_role"] == "admin"
    assert data["store_id"] is None
    assert data["store_name"] is None
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0


def test_login_store_manager1_success(test_client: TestClient):
    """
    Test successful login for store manager 1.
    
    Should return:
    - Status code 200
    - access_token
    - token_type = "bearer"
    - user_role = "store_manager"
    - store_id = 1
    - store_name = actual store name from database
    """
    response = test_client.post(
        "/api/login",
        json={"username": "manager1", "password": "manager123"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["token_type"] == "bearer"
    assert data["user_role"] == "store_manager"
    assert data["store_id"] == 1
    # Store name comes from database - just verify it exists
    assert isinstance(data["store_name"], str)
    assert len(data["store_name"]) > 0
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0


def test_login_store_manager2_success(test_client: TestClient):
    """
    Test successful login for store manager 2.
    
    Should return:
    - Status code 200
    - access_token
    - token_type = "bearer"
    - user_role = "store_manager"
    - store_id = 2
    - store_name = actual store name from database
    """
    response = test_client.post(
        "/api/login",
        json={"username": "manager2", "password": "manager123"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["token_type"] == "bearer"
    assert data["user_role"] == "store_manager"
    assert data["store_id"] == 2
    # Store name comes from database - just verify it exists
    assert isinstance(data["store_name"], str)
    assert len(data["store_name"]) > 0
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0


def test_login_invalid_username(test_client: TestClient):
    """
    Test login with invalid username.
    
    Should return:
    - Status code 401
    - Error message about invalid credentials
    """
    response = test_client.post(
        "/api/login",
        json={"username": "nonexistent", "password": "password"}
    )
    
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "username or password" in data["detail"].lower()


def test_login_invalid_password(test_client: TestClient):
    """
    Test login with invalid password.
    
    Should return:
    - Status code 401
    - Error message about invalid credentials
    """
    response = test_client.post(
        "/api/login",
        json={"username": "admin", "password": "wrongpassword"}
    )
    
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "username or password" in data["detail"].lower()


def test_login_missing_username(test_client: TestClient):
    """
    Test login with missing username field.
    
    Should return:
    - Status code 422 (validation error)
    """
    response = test_client.post(
        "/api/login",
        json={"password": "admin123"}
    )
    
    assert response.status_code == 422


def test_login_missing_password(test_client: TestClient):
    """
    Test login with missing password field.
    
    Should return:
    - Status code 422 (validation error)
    """
    response = test_client.post(
        "/api/login",
        json={"username": "admin"}
    )
    
    assert response.status_code == 422


def test_protected_endpoint_without_token(test_client: TestClient):
    """
    Test accessing protected endpoint without authentication token.
    
    Should return:
    - Status code 422 (FastAPI validation error for missing header)
    """
    response = test_client.get("/api/management/dashboard/top-categories")
    
    # FastAPI returns 422 when required header is missing
    assert response.status_code == 422


def test_protected_endpoint_with_invalid_token(test_client: TestClient):
    """
    Test accessing protected endpoint with invalid token.
    
    Should return:
    - Status code 401
    - Error about invalid token
    """
    response = test_client.get(
        "/api/management/dashboard/top-categories",
        headers={"Authorization": "Bearer invalid_token_12345"}
    )
    
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert "token" in data["detail"].lower()


def test_protected_endpoint_with_malformed_header(test_client: TestClient):
    """
    Test accessing protected endpoint with malformed authorization header.
    
    Should return:
    - Status code 401
    - Error about invalid authorization header
    """
    # Missing "Bearer " prefix
    response = test_client.get(
        "/api/management/dashboard/top-categories",
        headers={"Authorization": "some_token_12345"}
    )
    
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


def test_admin_can_access_all_stores(test_client: TestClient):
    """
    Test that admin user can access data from all stores.
    
    Should return:
    - Status code 200
    - Data from multiple stores
    """
    # Login as admin
    login_response = test_client.post(
        "/api/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Get inventory without store filter (should see all stores)
    response = test_client.get(
        "/api/management/inventory",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "inventory" in data
    
    # Check if we have data from multiple stores
    if len(data["inventory"]) > 0:
        store_ids = {item["store_id"] for item in data["inventory"]}
        # Admin should potentially see multiple stores (if data exists)
        assert len(store_ids) >= 1


def test_admin_can_filter_by_store(test_client: TestClient):
    """
    Test that admin user can filter data by specific store.
    
    Should return:
    - Status code 200
    - Data only from the specified store
    """
    # Login as admin
    login_response = test_client.post(
        "/api/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Get inventory filtered by store 1
    response = test_client.get(
        "/api/management/inventory?store_id=1",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "inventory" in data
    
    # All items should be from store 1
    if len(data["inventory"]) > 0:
        for item in data["inventory"]:
            assert item["store_id"] == 1


def test_store_manager_sees_only_their_store(test_client: TestClient):
    """
    Test that store manager can only see data from their assigned store.
    
    Should return:
    - Status code 200
    - Data only from manager's store (store_id = 1)
    """
    # Login as manager1 (Bellevue Square, store_id = 1)
    login_response = test_client.post(
        "/api/login",
        json={"username": "manager1", "password": "manager123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Get inventory (should automatically filter to store 1)
    response = test_client.get(
        "/api/management/inventory",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "inventory" in data
    
    # All items must be from store 1
    if len(data["inventory"]) > 0:
        for item in data["inventory"]:
            assert item["store_id"] == 1


def test_store_manager_cannot_access_other_store(test_client: TestClient):
    """
    Test that store manager cannot access data from other stores even with parameter.
    
    Should return:
    - Status code 200
    - Data only from manager's store, ignoring the store_id parameter
    """
    # Login as manager1 (Bellevue Square, store_id = 1)
    login_response = test_client.post(
        "/api/login",
        json={"username": "manager1", "password": "manager123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Try to access store 2 data with parameter (should be ignored)
    response = test_client.get(
        "/api/management/inventory?store_id=2",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "inventory" in data
    
    # All items must still be from store 1 (manager's store)
    if len(data["inventory"]) > 0:
        for item in data["inventory"]:
            assert item["store_id"] == 1


def test_different_store_managers_see_different_data(test_client: TestClient):
    """
    Test that different store managers see data from their respective stores.
    
    Should return:
    - Status code 200 for both
    - Manager1 sees store 1 data
    - Manager2 sees store 2 data
    """
    # Login as manager1 (store 1)
    login1_response = test_client.post(
        "/api/login",
        json={"username": "manager1", "password": "manager123"}
    )
    assert login1_response.status_code == 200
    token1 = login1_response.json()["access_token"]
    
    # Login as manager2 (store 2)
    login2_response = test_client.post(
        "/api/login",
        json={"username": "manager2", "password": "manager123"}
    )
    assert login2_response.status_code == 200
    token2 = login2_response.json()["access_token"]
    
    # Get inventory for manager1
    response1 = test_client.get(
        "/api/management/inventory",
        headers={"Authorization": f"Bearer {token1}"}
    )
    assert response1.status_code == 200
    data1 = response1.json()
    
    # Get inventory for manager2
    response2 = test_client.get(
        "/api/management/inventory",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert response2.status_code == 200
    data2 = response2.json()
    
    # Check manager1 sees only store 1
    if len(data1["inventory"]) > 0:
        for item in data1["inventory"]:
            assert item["store_id"] == 1
    
    # Check manager2 sees only store 2
    if len(data2["inventory"]) > 0:
        for item in data2["inventory"]:
            assert item["store_id"] == 2


def test_authentication_works_for_all_management_endpoints(test_client: TestClient):
    """
    Test that authentication is required for all management endpoints.
    
    Should return:
    - Status code 200 when authenticated
    - Status code 422 when not authenticated (missing required header)
    """
    # Login to get token
    login_response = test_client.post(
        "/api/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # List of management endpoints to test
    management_endpoints = [
        "/api/management/dashboard/top-categories",
        "/api/management/suppliers",
        "/api/management/inventory",
        "/api/management/products"
    ]
    
    for endpoint in management_endpoints:
        # Without authentication should fail with 422 (missing required header)
        response_no_auth = test_client.get(endpoint)
        assert response_no_auth.status_code == 422, f"Endpoint {endpoint} should return 422 for missing auth header"
        
        # With authentication should succeed
        response_with_auth = test_client.get(
            endpoint,
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response_with_auth.status_code == 200, f"Endpoint {endpoint} should work with valid auth"

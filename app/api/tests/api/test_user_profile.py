"""
Tests for user profile endpoints.
"""

import pytest
from fastapi.testclient import TestClient


def test_get_user_profile_success(test_client: TestClient):
    """
    Test successful retrieval of profile for a customer user.
    
    Should return:
    - Status code 200
    - Customer profile with first name, last name, email, etc.
    """
    # Login as customer
    login_response = test_client.post(
        "/api/login",
        json={"username": "tracey.lopez.4", "password": "tracey123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    
    # Get profile
    response = test_client.get(
        "/api/users/profile",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "customer_id" in data
    assert "first_name" in data
    assert "last_name" in data
    assert "email" in data
    
    # Verify customer ID matches
    assert data["customer_id"] == 4
    
    # Verify it's a real name, not empty
    assert len(data["first_name"]) > 0
    assert len(data["last_name"]) > 0


def test_get_user_profile_unauthorized(test_client: TestClient):
    """
    Test that profile endpoint requires authentication.
    
    Should return:
    - Status code 422 (missing header) or 401 (invalid token)
    """
    response = test_client.get("/api/users/profile")
    
    assert response.status_code == 422  # Missing header


def test_get_user_profile_invalid_token(test_client: TestClient):
    """
    Test that profile endpoint rejects invalid token.
    
    Should return:
    - Status code 401
    """
    response = test_client.get(
        "/api/users/profile",
        headers={"Authorization": "Bearer invalid_token"}
    )
    
    assert response.status_code == 401


def test_get_user_profile_forbidden_for_admin(test_client: TestClient):
    """
    Test that admin users cannot access customer profile endpoint.
    
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
    
    # Try to get profile
    response = test_client.get(
        "/api/users/profile",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 403
    assert "customer" in response.json()["detail"].lower()


def test_get_user_profile_forbidden_for_store_manager(test_client: TestClient):
    """
    Test that store manager users cannot access customer profile endpoint.
    
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
    
    # Try to get profile
    response = test_client.get(
        "/api/users/profile",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 403
    assert "customer" in response.json()["detail"].lower()

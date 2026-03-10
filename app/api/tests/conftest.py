"""
Pytest configuration and fixtures for API testing.

This module provides shared fixtures and configuration for all tests.
"""

import os
from unittest.mock import patch

# Set required environment variables before any other imports
# These are needed by Settings class in openid_auth.py
os.environ.setdefault("KEYCLOAK_SERVER_URL", "http://localhost:8080")
os.environ.setdefault("KEYCLOAK_REALM", "test-realm")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "test-client")
os.environ.setdefault("KEYCLOAK_CLIENT_SECRET", "test-secret")
os.environ.setdefault("SQLITE_DATABASE_PATH", ":memory:")

import pytest
from fastapi.testclient import TestClient
from typing import Generator

from zava_shop_api.models import TokenData
from zava_shop_api.openid_auth import USERS


_TEST_PASSWORDS: dict[str, str] = {
    "admin": "admin123",
    "manager1": "manager123",
    "manager2": "manager123",
    "stacey": "stacey123",
    "tracey.lopez.4": "tracey123",
    "marketing": "marketing123",
}


def _make_fake_authenticate(username: str, password: str) -> tuple[str, TokenData]:
    """Fake authenticate_user that doesn't need Keycloak."""
    from fastapi import HTTPException, status as http_status

    user = USERS.get(username)
    expected_pw = _TEST_PASSWORDS.get(username)
    if user is None or expected_pw is None or expected_pw != password:
        raise HTTPException(status_code=http_status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    fake_token = f"fake-jwt-{username}"
    return fake_token, TokenData(
        username=username,
        user_role=user.role,
        store_id=user.store_id,
        customer_id=user.customer_id,
        access_token=fake_token,
    )


def _make_fake_verify(token: str) -> TokenData:
    """Fake verify_token that accepts fake-jwt-* tokens."""
    from fastapi import HTTPException

    if token.startswith("fake-jwt-"):
        username = token.removeprefix("fake-jwt-")
        user = USERS.get(username)
        if user:
            return TokenData(
                username=username,
                user_role=user.role,
                store_id=user.store_id,
                customer_id=user.customer_id,
                access_token=token,
            )
    raise HTTPException(status_code=401, detail="Invalid or expired token")


@pytest.fixture(scope="module")
def test_client() -> Generator[TestClient, None, None]:
    """
    Create a TestClient for the FastAPI application.

    Patches AuthService so tests don't require a running Keycloak server.
    """
    with (
        patch("zava_shop_api.openid_auth.AuthService.authenticate_user", side_effect=_make_fake_authenticate),
        patch("zava_shop_api.openid_auth.AuthService.verify_token", side_effect=_make_fake_verify),
    ):
        from zava_shop_api.app import app
        with TestClient(app) as client:
            yield client


@pytest.fixture(scope="function")
def admin_auth_headers(test_client: TestClient) -> dict:
    """
    Get authentication headers for admin user.
    
    Logs in as admin and returns headers with Bearer token.
    
    Args:
        test_client: The test client fixture
        
    Returns:
        dict: Headers with Authorization token
    """
    response = test_client.post(
        "/api/login",
        json={"username": "admin", "password": "admin123"}
    )
    assert response.status_code == 200, f"Admin login failed: {response.json()}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def customer_auth_headers(test_client: TestClient) -> dict:
    """
    Get authentication headers for customer user.
    
    Logs in as customer and returns headers with Bearer token.
    
    Args:
        test_client: The test client fixture
        
    Returns:
        dict: Headers with Authorization token
    """
    response = test_client.post(
        "/api/login",
        json={"username": "tracey.lopez.4", "password": "tracey123"}
    )
    assert response.status_code == 200, f"Customer login failed: {response.json()}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def store_manager_auth_headers(test_client: TestClient) -> dict:
    """
    Get authentication headers for store manager user.
    
    Logs in as store manager and returns headers with Bearer token.
    
    Args:
        test_client: The test client fixture
        
    Returns:
        dict: Headers with Authorization token
    """
    response = test_client.post(
        "/api/login",
        json={"username": "manager1", "password": "manager123"}
    )
    assert response.status_code == 200, f"Manager login failed: {response.json()}"
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def test_db():
    """
    Create a test database connection.
    
    This fixture will be used to set up and tear down test database
    instances for integration testing.
    
    TODO: Implement when switching to SQLAlchemy/SQLite
    """
    pass


@pytest.fixture(scope="function")
def sample_store_data():
    """
    Provide sample store data for testing.
    
    Returns:
        dict: Sample store data matching the Store Pydantic model
    """
    return {
        "id": 1,
        "name": "Test Store",
        "location": "Test Location",
        "is_online": False,
        "location_key": "test_location",
        "products": 10,
        "total_stock": 100,
        "inventory_value": 5000.00,
        "status": "Open",
        "hours": "Mon-Sun: 10am-7pm"
    }


@pytest.fixture(scope="function")
def sample_category_data():
    """
    Provide sample category data for testing.
    
    Returns:
        dict: Sample category data matching the Category Pydantic model
    """
    return {
        "id": 1,
        "name": "Test Category"
    }


@pytest.fixture(scope="function")
def sample_product_data():
    """
    Provide sample product data for testing.
    
    Returns:
        dict: Sample product data matching the Product Pydantic model
    """
    return {
        "product_id": 1,
        "sku": "TEST-001",
        "product_name": "Test Product",
        "category_name": "Test Category",
        "type_name": "Test Type",
        "unit_price": 99.99,
        "cost": 50.00,
        "gross_margin_percent": 50.0,
        "product_description": "A test product",
        "supplier_name": "Test Supplier",
        "discontinued": False,
        "image_url": "/images/test.jpg"
    }


@pytest.fixture(scope="function")
def sample_supplier_data():
    """
    Provide sample supplier data for testing.
    
    Returns:
        dict: Sample supplier data matching the Supplier Pydantic model
    """
    return {
        "id": 1,
        "name": "Test Supplier",
        "code": "SUP001",
        "location": "Test City, State",
        "contact": "test@supplier.com",
        "phone": "(555) 123-4567",
        "rating": 4.5,
        "esg_compliant": True,
        "approved": True,
        "preferred": True,
        "categories": ["Category 1", "Category 2"],
        "lead_time": 7,
        "payment_terms": "Net 30",
        "min_order": 1000.00,
        "bulk_discount": 5.0
    }


@pytest.fixture(scope="function")
def sample_inventory_item_data():
    """
    Provide sample inventory item data for testing.
    
    Returns:
        dict: Sample inventory item data matching the InventoryItem Pydantic model
    """
    return {
        "store_id": 1,
        "store_name": "Test Store",
        "store_location": "Test Location",
        "is_online": False,
        "product_id": 1,
        "product_name": "Test Product",
        "sku": "TEST-001",
        "category": "Test Category",
        "type": "Test Type",
        "stock_level": 50,
        "reorder_point": 10,
        "is_low_stock": False,
        "unit_cost": 50.00,
        "unit_price": 99.99,
        "stock_value": 2500.00,
        "retail_value": 4999.50,
        "supplier_name": "Test Supplier",
        "supplier_code": "SUP001",
        "lead_time": 7,
        "image_url": "/images/test.jpg"
    }

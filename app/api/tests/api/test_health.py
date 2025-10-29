"""
Tests for health check and root endpoints.
"""

from fastapi.testclient import TestClient


def test_health_check(test_client: TestClient):
    """Health endpoint returns status and database info."""
    response = test_client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


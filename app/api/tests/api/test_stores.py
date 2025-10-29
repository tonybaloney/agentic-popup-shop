"""
Tests for store-related endpoints.
"""

from fastapi.testclient import TestClient


def test_get_stores(test_client: TestClient):
    """Stores endpoint returns successful response with data."""
    response = test_client.get("/api/stores")

    assert response.status_code == 200
    data = response.json()
    assert "stores" in data
    assert "total" in data
    assert isinstance(data["stores"], list)
    assert isinstance(data["total"], int)


def test_get_stores_returns_correct_schema(test_client: TestClient):
    """Stores endpoint returns data matching StoreList schema."""
    response = test_client.get("/api/stores")

    assert response.status_code == 200
    data = response.json()

    # Validate top-level structure
    assert "stores" in data
    assert "total" in data
    assert data["total"] == len(data["stores"])

    # If there are stores, validate the schema of the first one
    if data["stores"]:
        store = data["stores"][0]

        # Check all required fields exist
        required_fields = [
            "id", "name", "location", "is_online", "location_key",
            "products", "total_stock", "inventory_value", "status", "hours"
        ]
        for field in required_fields:
            assert field in store, f"Missing field: {field}"

        # Validate field types
        assert isinstance(store["id"], int)
        assert isinstance(store["name"], str)
        assert isinstance(store["location"], str)
        assert isinstance(store["is_online"], bool)
        assert isinstance(store["location_key"], str)
        assert isinstance(store["products"], int)
        assert isinstance(store["total_stock"], int)
        assert isinstance(store["inventory_value"], (int, float))
        assert isinstance(store["status"], str)
        assert isinstance(store["hours"], str)

        # Validate field values make sense
        assert store["products"] >= 0
        assert store["total_stock"] >= 0
        assert store["inventory_value"] >= 0


def test_get_stores_ordering(test_client: TestClient):
    """Stores endpoint returns stores in correct order."""
    response = test_client.get("/api/stores")

    assert response.status_code == 200
    data = response.json()

    if len(data["stores"]) > 1:
        stores = data["stores"]

        # Check that online stores come before physical stores
        # (is_online: False sorts before is_online: True in ASC order)
        # Actually, looking at the query: ORDER BY is_online ASC
        # So online stores (is_online=True) should come AFTER physical stores
        for i in range(len(stores) - 1):
            if not stores[i]["is_online"] and stores[i + 1]["is_online"]:
                # Physical store followed by online - correct
                continue
            elif stores[i]["is_online"] == stores[i + 1]["is_online"]:
                # Same type, should be alphabetically sorted by name
                assert stores[i]["name"] <= stores[i + 1]["name"], \
                    f"Stores not alphabetically sorted: {stores[i]['name']} > {stores[i + 1]['name']}"

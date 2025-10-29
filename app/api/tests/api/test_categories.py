"""
Tests for category-related endpoints.
"""

from fastapi.testclient import TestClient


def test_get_categories(test_client: TestClient):
    """Categories endpoint returns successful response with data."""
    response = test_client.get("/api/categories")

    assert response.status_code == 200
    data = response.json()
    assert "categories" in data
    assert "total" in data
    assert isinstance(data["categories"], list)
    assert isinstance(data["total"], int)
    assert data["total"] == len(data["categories"])


def test_get_categories_returns_correct_schema(test_client: TestClient):
    """Categories endpoint returns data matching CategoryList schema."""
    response = test_client.get("/api/categories")

    assert response.status_code == 200
    data = response.json()

    # Validate top-level structure
    assert "categories" in data
    assert "total" in data

    # If there are categories, validate the schema
    if data["categories"]:
        category = data["categories"][0]

        # Check all required fields exist
        assert "id" in category
        assert "name" in category

        # Validate field types
        assert isinstance(category["id"], int)
        assert isinstance(category["name"], str)

        # Validate id is positive
        assert category["id"] > 0
        assert len(category["name"]) > 0


def test_get_categories_alphabetically_ordered(test_client: TestClient):
    """Categories endpoint returns categories in alphabetical order."""
    response = test_client.get("/api/categories")

    assert response.status_code == 200
    data = response.json()

    if len(data["categories"]) > 1:
        categories = data["categories"]

        # Check that categories are alphabetically sorted by name
        for i in range(len(categories) - 1):
            current_name = categories[i]["name"]
            next_name = categories[i + 1]["name"]
            assert current_name <= next_name, \
                f"Categories not alphabetically sorted: {current_name} > {next_name}"

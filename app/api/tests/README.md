# Test Suite for Popup Store API

This directory contains the test suite for the FastAPI backend.

## Structure

```
tests/
├── __init__.py
├── conftest.py           # Shared pytest fixtures and configuration
├── README.md            # This file
└── api/                 # API endpoint tests
    ├── __init__.py
    ├── test_health.py                  # Health check and root endpoint tests
    ├── test_stores.py                  # Store endpoints
    ├── test_categories.py              # Category endpoints
    ├── test_products.py                # Product endpoints
    ├── test_management_dashboard.py    # Dashboard endpoints
    ├── test_management_suppliers.py    # Supplier management
    ├── test_management_inventory.py    # Inventory management
    └── test_management_products.py     # Product management
```

## Running Tests

### Run all tests
```bash
pytest
```

### Run specific test file
```bash
pytest tests/api/test_stores.py
```

### Run specific test class
```bash
pytest tests/api/test_stores.py::TestStoresEndpoints
```

### Run specific test
```bash
pytest tests/api/test_stores.py::TestStoresEndpoints::test_get_stores
```

### Run tests with coverage
```bash
pytest --cov=app --cov-report=html
```

### Run tests with specific markers
```bash
pytest -m unit          # Run only unit tests
pytest -m integration   # Run only integration tests
pytest -m "not slow"    # Skip slow tests
```

## Test Categories

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests (isolated, fast, no external dependencies)
- `@pytest.mark.integration` - Integration tests (require database)
- `@pytest.mark.slow` - Tests that take significant time
- `@pytest.mark.api` - API endpoint tests

## Fixtures

Common fixtures are defined in `conftest.py`:

- `test_client` - FastAPI TestClient for making API requests
- `test_db` - Test database connection (to be implemented with SQLAlchemy)
- `sample_*_data` - Sample data for various models

## Writing Tests

### Example API Test

```python
import pytest
from fastapi.testclient import TestClient

class TestMyEndpoint:
    def test_get_endpoint(self, test_client: TestClient):
        """Test GET /api/my-endpoint."""
        response = test_client.get("/api/my-endpoint")
        
        assert response.status_code == 200
        data = response.json()
        assert "key" in data
```

### Example with Fixtures

```python
def test_with_sample_data(self, test_client: TestClient, sample_store_data):
    """Test using sample data fixture."""
    # Use sample_store_data in your test
    assert sample_store_data["id"] == 1
```

## TODO

Current test files contain skeleton test methods with TODO comments.
These need to be implemented with actual test logic.

When implementing tests:
1. Use the TestClient fixture for API calls
2. Assert expected status codes
3. Validate response schema matches Pydantic models
4. Test edge cases and error conditions
5. Add appropriate markers (@pytest.mark.unit, etc.)

## Notes for SQLAlchemy Migration

When migrating to SQLAlchemy/SQLite:
- Update `test_db` fixture in `conftest.py` to create test database
- Add fixtures for creating test data in the database
- Consider using `pytest-asyncio` for async database operations
- Add database cleanup between tests
- Use transactions for test isolation

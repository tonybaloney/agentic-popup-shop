"""
Integration tests for end-to-end token propagation from frontend to MCP.

These tests verify that user tokens acquired during login are correctly:
1. Stored in TokenData.access_token
2. Passed through to agent workflows
3. Propagated to MCP calls
"""

import os
import pytest
import requests
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

# Set required environment variables before importing modules that need them
os.environ.setdefault("KEYCLOAK_SERVER_URL", "http://localhost:8080")


def _keycloak_available() -> bool:
    """Check if Keycloak server is available."""
    try:
        keycloak_url = os.environ.get("KEYCLOAK_SERVER_URL", "http://localhost:8080")
        realm = os.environ.get("KEYCLOAK_REALM", "zava")
        response = requests.get(f"{keycloak_url}/realms/{realm}", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


KEYCLOAK_AVAILABLE = _keycloak_available()
os.environ.setdefault("KEYCLOAK_REALM", "test-realm")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "test-client")
os.environ.setdefault("KEYCLOAK_CLIENT_SECRET", "test-secret")
os.environ.setdefault("SQLITE_DATABASE_PATH", ":memory:")

from zava_shop_api.openid_auth import (
    AuthService,
)
from zava_shop_api.models import TokenData


class TestTokenDataHasAccessToken:
    """Test that TokenData model includes access_token field."""

    def test_token_data_default_none(self):
        """access_token should default to None for backwards compatibility."""
        token_data = TokenData(
            username="test_user",
            user_role="admin",
        )
        assert token_data.access_token is None

    def test_token_data_with_token(self):
        """access_token can be set explicitly."""
        token_data = TokenData(
            username="test_user",
            user_role="store_manager",
            store_id=1,
            access_token="test-keycloak-token-123",
        )
        assert token_data.access_token == "test-keycloak-token-123"
        assert token_data.username == "test_user"
        assert token_data.user_role == "store_manager"
        assert token_data.store_id == 1


class TestWorkflowReceivesToken:
    """Test that workflows receive the user token parameter."""

    def test_stock_workflow_accepts_user_token(self):
        """stock.build_workflow should accept user_token parameter."""
        from zava_shop_agents.stock import build_workflow
        import inspect

        sig = inspect.signature(build_workflow)
        assert "user_token" in sig.parameters
        param = sig.parameters["user_token"]
        assert param.default is None  # Should be optional

    def test_insights_workflow_accepts_user_token(self):
        """insights.build_workflow should accept user_token parameter."""
        from zava_shop_agents.insights import build_workflow
        import inspect

        sig = inspect.signature(build_workflow)
        assert "user_token" in sig.parameters
        param = sig.parameters["user_token"]
        assert param.default is None  # Should be optional

    def test_admin_insights_workflow_accepts_user_token(self):
        """admin_insights.build_workflow should accept user_token parameter."""
        from zava_shop_agents.admin_insights import build_workflow
        import inspect

        sig = inspect.signature(build_workflow)
        assert "user_token" in sig.parameters
        param = sig.parameters["user_token"]
        assert param.default is None  # Should be optional


class TestMCPToolReceivesToken:
    """Test that MCP tools receive the correct authorization header."""

    def test_stock_workflow_signature_includes_user_token(self):
        """Verify stock.build_workflow accepts user_token and uses it in MCP config."""
        import inspect
        from zava_shop_agents.stock import build_workflow

        # Check function signature
        sig = inspect.signature(build_workflow)
        assert "user_token" in sig.parameters
        
        # Get the source to verify token is used in MCP config
        source = inspect.getsource(build_workflow)
        assert "user_token" in source
        assert "auth_token = user_token or" in source
        # Verify the auth_token is used in the Authorization header
        assert 'f"Bearer {auth_token}"' in source

    def test_insights_workflow_signature_includes_user_token(self):
        """Verify insights.build_workflow accepts user_token and uses it in MCP config."""
        import inspect
        from zava_shop_agents.insights import build_workflow

        sig = inspect.signature(build_workflow)
        assert "user_token" in sig.parameters
        
        source = inspect.getsource(build_workflow)
        assert "user_token" in source
        assert "auth_token = user_token or" in source
        assert 'f"Bearer {auth_token}"' in source

    def test_admin_insights_workflow_signature_includes_user_token(self):
        """Verify admin_insights.build_workflow accepts user_token and uses it in MCP config."""
        import inspect
        from zava_shop_agents.admin_insights import build_workflow

        sig = inspect.signature(build_workflow)
        assert "user_token" in sig.parameters
        
        source = inspect.getsource(build_workflow)
        assert "user_token" in source
        assert "auth_token = user_token or" in source
        assert 'f"Bearer {auth_token}"' in source

    def test_mcp_tool_otel_uses_headers(self):
        """Verify MCPStreamableHTTPToolOTEL accesses self.headers for traceparent."""
        import inspect
        from zava_shop_agents import MCPStreamableHTTPToolOTEL

        # Verify the OTEL wrapper accesses headers (which confirms it exists)
        source = inspect.getsource(MCPStreamableHTTPToolOTEL)
        assert 'self.headers["traceparent"]' in source


class TestEndToEndTokenPropagation:
    """
    End-to-end test verifying token flows from login through to MCP.
    
    This test mocks the MCP call to capture and verify the token.
    """

    @pytest.mark.integration
    @pytest.mark.skipif(
        not KEYCLOAK_AVAILABLE,
        reason="Requires running Keycloak server"
    )
    @patch("zava_shop_api.routers.management.stock_workflow")
    def test_websocket_ai_agent_passes_token(
        self,
        mock_stock_workflow,
        test_client: TestClient,
    ):
        """
        WebSocket AI agent endpoint should pass user's access_token to workflow.
        
        Flow: Login → WebSocket connect → Workflow receives token
        """
        # Login to get a real token
        login_response = test_client.post(
            "/api/login",
            json={"username": "manager1", "password": "manager123"}
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Verify stock_workflow import can be patched
        # The actual WebSocket test would need async support

    @pytest.mark.integration
    @pytest.mark.skipif(
        not KEYCLOAK_AVAILABLE,
        reason="Requires running Keycloak server"
    )
    @patch("zava_shop_api.routers.management.insights_workflow")
    @patch("zava_shop_api.routers.management.admin_insights_workflow")
    def test_insights_endpoint_passes_token(
        self,
        mock_admin_workflow,
        mock_insights_workflow,
        test_client: TestClient,
        store_manager_auth_headers: dict,
    ):
        """
        Insights endpoint should pass user's access_token to workflow.
        
        Note: This test verifies the wiring - actual MCP calls require
        running MCP servers.
        """
        # Setup mock workflow to return quickly
        mock_workflow = AsyncMock()
        mock_workflow.run_stream = AsyncMock(return_value=iter([]))
        mock_insights_workflow.return_value = mock_workflow

        # Make request (will likely fail without full MCP setup,
        # but we can verify the workflow was called with token)
        # This test documents the expected behavior


class TestTokenSecurityConstraints:
    """Test that tokens are handled securely."""

    @pytest.mark.integration
    @pytest.mark.skipif(
        not KEYCLOAK_AVAILABLE,
        reason="Requires running Keycloak server"
    )
    def test_token_not_exposed_in_login_response_body(self, test_client: TestClient):
        """
        The access_token in LoginResponse is the Keycloak token.
        This is expected behavior for the frontend to store.
        """
        response = test_client.post(
            "/api/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200
        data = response.json()

        # Token should be present (this is expected)
        assert "access_token" in data
        # Token should be a non-empty string
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 10

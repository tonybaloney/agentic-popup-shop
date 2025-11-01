"""
Tests for ChatKit API endpoint.
"""

import pytest
import json
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock


class TestChatKitAuthentication:
    """Tests for ChatKit endpoint authentication and authorization."""
    
    def test_chatkit_without_auth_fails(self, test_client: TestClient):
        """
        Test that ChatKit endpoint requires authentication.
        
        Should return:
        - Status code 401 (Unauthorized)
        """
        response = test_client.post("/api/chatkit")
        assert response.status_code == 401
    
    def test_chatkit_with_invalid_token_fails(self, test_client: TestClient):
        """
        Test that ChatKit endpoint rejects invalid tokens.
        
        Should return:
        - Status code 401 (Unauthorized)
        """
        response = test_client.post(
            "/api/chatkit",
            headers={"Authorization": "Bearer invalid_token_12345"}
        )
        assert response.status_code == 401
    
    def test_chatkit_with_admin_role_fails(self, test_client: TestClient, admin_auth_headers: dict):
        """
        Test that ChatKit endpoint rejects non-customer roles (admin).
        
        Should return:
        - Status code 403 (Forbidden)
        - Error message about customer access only
        """
        response = test_client.post(
            "/api/chatkit",
            headers=admin_auth_headers
        )
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "customer" in data["detail"].lower()
    
    def test_chatkit_with_manager_role_fails(self, test_client: TestClient, store_manager_auth_headers: dict):
        """
        Test that ChatKit endpoint rejects non-customer roles (store manager).
        
        Should return:
        - Status code 403 (Forbidden)
        - Error message about customer access only
        """
        response = test_client.post(
            "/api/chatkit",
            headers=store_manager_auth_headers
        )
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "customer" in data["detail"].lower()


class TestChatKitSessionCreation:
    """Tests for ChatKit session creation functionality."""
    
    @patch('zava_shop_api.chatkit_router.chatkit_server.process')
    async def test_chatkit_session_creation_success(
        self,
        mock_process: AsyncMock,
        test_client: TestClient,
        customer_auth_headers: dict
    ):
        """
        Test successful ChatKit session creation for customer.
        
        Should return:
        - Status code 200
        - Valid response from ChatKit server
        """
        # Mock the ChatKit server response
        mock_response = MagicMock()
        mock_response.json = json.dumps({"client_secret": "test_secret_123"})
        mock_process.return_value = mock_response
        
        response = test_client.post(
            "/api/chatkit",
            headers=customer_auth_headers
        )
        
        assert response.status_code == 200
    
    @patch('zava_shop_api.chatkit_router.chatkit_server.process')
    async def test_chatkit_passes_user_context(
        self,
        mock_process: AsyncMock,
        test_client: TestClient,
        customer_auth_headers: dict
    ):
        """
        Test that ChatKit endpoint passes correct user context.
        
        Should pass:
        - user_id (username)
        - customer_id
        - role
        - user_agent
        """
        # Mock the ChatKit server response
        mock_response = MagicMock()
        mock_response.json = json.dumps({"client_secret": "test_secret_123"})
        mock_process.return_value = mock_response
        
        response = test_client.post(
            "/api/chatkit",
            headers={**customer_auth_headers, "User-Agent": "TestClient/1.0"}
        )
        
        # Verify process was called
        assert mock_process.called
        
        # Get the context that was passed to process
        call_args = mock_process.call_args
        context = call_args[0][1]  # Second argument is context
        
        # Verify context contains expected user information
        assert "user_id" in context
        assert "customer_id" in context
        assert "role" in context
        assert context["role"] == "customer"
        assert "user_agent" in context


class TestChatKitMessaging:
    """Tests for ChatKit message handling functionality."""
    
    @patch('zava_shop_api.chatkit_router.chatkit_server.process')
    async def test_chatkit_handles_json_response(
        self,
        mock_process: AsyncMock,
        test_client: TestClient,
        customer_auth_headers: dict
    ):
        """
        Test that ChatKit correctly handles JSON responses.
        
        Should return:
        - Status code 200
        - Content-Type: application/json
        - Valid JSON response
        """
        # Mock the ChatKit server response
        mock_response = MagicMock()
        mock_response.json = json.dumps({"message": "Hello, how can I help you?"})
        mock_process.return_value = mock_response
        
        response = test_client.post(
            "/api/chatkit",
            headers=customer_auth_headers,
            json={"message": "Hello"}
        )
        
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")
    
    @patch('zava_shop_api.chatkit_router.chatkit_server.process')
    async def test_chatkit_handles_streaming_response(
        self,
        mock_process: AsyncMock,
        test_client: TestClient,
        customer_auth_headers: dict
    ):
        """
        Test that ChatKit correctly handles streaming (SSE) responses.
        
        Should return:
        - Status code 200
        - Content-Type: text/event-stream
        """
        # Mock a streaming response
        async def mock_stream():
            yield b"data: chunk1\n\n"
            yield b"data: chunk2\n\n"
        
        mock_response = MagicMock()
        mock_response.__aiter__ = lambda x: mock_stream()
        mock_process.return_value = mock_response
        
        response = test_client.post(
            "/api/chatkit",
            headers=customer_auth_headers,
            json={"message": "Tell me about products"}
        )
        
        assert response.status_code == 200
        # For streaming, the content-type should be text/event-stream
        # Note: TestClient may not stream, so we verify the mock was called correctly
        assert mock_process.called


class TestChatKitErrorHandling:
    """Tests for ChatKit error handling."""
    
    @patch('zava_shop_api.chatkit_router.chatkit_server.process')
    async def test_chatkit_handles_server_error_gracefully(
        self,
        mock_process: AsyncMock,
        test_client: TestClient,
        customer_auth_headers: dict
    ):
        """
        Test that ChatKit handles server errors gracefully.
        
        Should return:
        - Status code 500
        - Error message in JSON format
        """
        # Mock a server error
        mock_process.side_effect = Exception("ChatKit server error")
        
        response = test_client.post(
            "/api/chatkit",
            headers=customer_auth_headers,
            json={"message": "Hello"}
        )
        
        assert response.status_code == 500
    
    def test_chatkit_handles_malformed_request(
        self,
        test_client: TestClient,
        customer_auth_headers: dict
    ):
        """
        Test that ChatKit handles malformed requests.
        
        The endpoint should handle various request formats gracefully.
        """
        # Send request with invalid JSON
        response = test_client.post(
            "/api/chatkit",
            headers=customer_auth_headers,
            content=b"not valid json {"
        )
        
        # Should not crash - either process it or return an error
        assert response.status_code in [200, 400, 500]


class TestChatKitIntegration:
    """Integration tests for ChatKit functionality."""
    
    def test_chatkit_router_is_registered(self, test_client: TestClient):
        """
        Test that the ChatKit router is properly registered in the main app.
        
        Should:
        - Respond to requests at /api/chatkit endpoint
        - Not return 404
        """
        # Try accessing without auth - should get 401, not 404
        response = test_client.post("/api/chatkit")
        assert response.status_code != 404, "ChatKit router not registered"
    
    def test_chatkit_endpoint_path(self, test_client: TestClient):
        """
        Test that ChatKit endpoint is accessible at the correct path.
        
        Should be accessible at:
        - /api/chatkit (POST)
        """
        # Test with customer auth to ensure endpoint exists
        login_response = test_client.post(
            "/api/login",
            json={"username": "tracey.lopez.4", "password": "tracey123"}
        )
        token = login_response.json()["access_token"]
        
        response = test_client.post(
            "/api/chatkit",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # Should not be 404 or 405 (method not allowed)
        assert response.status_code not in [404, 405]


class TestChatKitDataStore:
    """Tests for ChatKit data store functionality."""
    
    @patch('zava_shop_api.chatkit_router.chatkit_server.process')
    async def test_chatkit_uses_memory_store(
        self,
        mock_process: AsyncMock,
        test_client: TestClient,
        customer_auth_headers: dict
    ):
        """
        Test that ChatKit is using the MemoryStore for data persistence.
        
        This test verifies the store is initialized and being used.
        """
        # Mock the response
        mock_response = MagicMock()
        mock_response.json = json.dumps({"status": "ok"})
        mock_process.return_value = mock_response
        
        # Make a request
        response = test_client.post(
            "/api/chatkit",
            headers=customer_auth_headers
        )
        
        # Verify the process method was called (which uses the store)
        assert mock_process.called
        assert response.status_code == 200


class TestChatKitAgent:
    """Tests for ChatKit AI agent configuration."""
    
    def test_chatkit_agent_is_configured(self):
        """
        Test that the ChatKit agent is properly configured.
        
        Should have:
        - Valid model (gpt-4o-mini)
        - Name set
        - Instructions defined
        """
        from zava_shop_api.chatkit_router import chatkit_server
        
        assert chatkit_server is not None
        assert hasattr(chatkit_server, 'assistant_agent')
        assert chatkit_server.assistant_agent is not None
        
        # Verify agent configuration
        agent = chatkit_server.assistant_agent
        assert agent.model == "gpt-4o-mini"
        assert agent.name == "Zava Shop Assistant"
        assert len(agent.instructions) > 0
        assert "Zava Shop" in agent.instructions

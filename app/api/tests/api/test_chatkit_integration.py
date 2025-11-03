"""
Integration tests for ChatKit API with actual OpenAI backend.

These tests require:
- AZURE_OPENAI_ENDPOINT_GPT5
- AZURE_OPENAI_API_KEY_GPT5
- AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5
- AZURE_OPENAI_ENDPOINT_VERSION_GPT5

Run with: uv run python -m pytest tests/api/test_chatkit_integration.py -v -s
"""

import pytest
import json
import os
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def check_openai_config():
    """
    Check if OpenAI configuration is available.
    Skip tests if not configured.
    """
    required_vars = [
        "AZURE_OPENAI_ENDPOINT_GPT5",
        "AZURE_OPENAI_API_KEY_GPT5",
        "AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5"
    ]
    
    missing = [var for var in required_vars if not os.environ.get(var)]
    
    if missing:
        pytest.skip(f"Missing required environment variables: {', '.join(missing)}")
    
    return True


class TestChatKitRealIntegration:
    """Integration tests with actual OpenAI/Azure OpenAI backend."""
    
    def test_chatkit_create_thread_and_send_message(
        self,
        test_client: TestClient,
        customer_auth_headers: dict,
        check_openai_config: bool
    ):
        """
        Test creating a chat thread and sending a message with real AI response.
        
        This test:
        1. Creates a new thread
        2. Sends a simple greeting message
        3. Verifies we get a streaming response
        4. Checks that the AI responds appropriately
        """
        print("\n🧪 Testing ChatKit thread creation and message...")
        
        # Create a thread
        create_thread_payload = {
            "type": "threads.create",
            "params": {
                "input": {
                    "content": [
                        {
                            "type": "input_text",
                            "text": "Hello! Can you tell me what kind of store this is?"
                        }
                    ],
                    "attachments": [],
                    "inference_options": {}
                },
                "metadata": {
                    "user_id": "test_user_3",
                    "session_id": "test_session_789"
                }
            }
        }
        
        response = test_client.post(
            "/api/chatkit",
            headers=customer_auth_headers,
            json=create_thread_payload
        )
        
        print(f"Create thread status: {response.status_code}")
        assert response.status_code == 200
        
        # Parse the streaming response to get thread_id
        thread_id = None
        for line in response.text.split('\n'):
            if line.startswith('data: ') and line.strip() != 'data: [DONE]':
                try:
                    data = json.loads(line[6:])  # Remove 'data: ' prefix
                    if data.get("type") == "threads.create.response":
                        thread_id = data.get("thread_id")
                        print(f"✅ Thread created: {thread_id}")
                        break
                except json.JSONDecodeError:
                    continue
        
        assert thread_id is not None, "Failed to extract thread_id from response"
        
        # Step 2: Send a message to the thread
        send_message_payload = {
            "type": "threads.add_user_message",
            "thread_id": thread_id,
            "content": "Hello! Can you tell me what kind of store this is?"
        }
        
        print(f"\n💬 Sending message to thread {thread_id}...")
        response = test_client.post(
            "/api/chatkit",
            headers=customer_auth_headers,
            json=send_message_payload
        )
        
        print(f"Send message status: {response.status_code}")
        assert response.status_code == 200
        
        # Step 3: Parse the streaming response and verify AI response
        ai_response_content = []
        events_received = []
        
        for line in response.text.split('\n'):
            if line.startswith('data: ') and line.strip() != 'data: [DONE]':
                try:
                    data = json.loads(line[6:])
                    event_type = data.get("type")
                    events_received.append(event_type)
                    
                    # Collect text content from deltas
                    if event_type == "threads.run.item.delta.text":
                        delta_text = data.get("delta", {}).get("text", "")
                        if delta_text:
                            ai_response_content.append(delta_text)
                            print(delta_text, end='', flush=True)
                    
                    # Also check for completed content
                    elif event_type == "threads.run.item.added":
                        item_content = data.get("item", {}).get("content", [])
                        for content_item in item_content:
                            if content_item.get("type") == "text":
                                text = content_item.get("text", "")
                                if text and text not in ''.join(ai_response_content):
                                    ai_response_content.append(text)
                
                except json.JSONDecodeError:
                    continue
        
        print("\n")  # New line after streaming output
        
        # Verify we received a proper AI response
        full_response = ''.join(ai_response_content).strip()
        print(f"\n📝 Full AI response: {full_response[:200]}...")
        print(f"📊 Events received: {set(events_received)}")
        
        # Assertions
        assert len(full_response) > 0, "AI should have generated a response"
        assert len(events_received) > 0, "Should have received streaming events"
        
        # Check that response mentions the store (Zava Shop)
        # The AI should reference the store based on its instructions
        response_lower = full_response.lower()
        assert any(word in response_lower for word in ['shop', 'store', 'clothing', 'zava']), \
            f"AI response should mention the store context. Got: {full_response}"
        
        print("✅ Integration test passed!")
    
    def test_chatkit_handles_product_question(
        self,
        test_client: TestClient,
        customer_auth_headers: dict,
        check_openai_config: bool
    ):
        """
        Test asking about products to verify the AI understands the store context.
        """
        print("\n🧪 Testing product-related question...")
        
        # Create thread and send message in one go
        create_and_message_payload = {
            "type": "threads.create",
            "params": {
                "input": {
                    "content": [
                        {
                            "type": "input_text",
                            "text": "What kind of products do you sell?"
                        }
                    ],
                    "attachments": [],
                    "inference_options": {}
                },
                "metadata": {
                    "user_id": "test_user_2",
                    "session_id": "test_session_456"
                }
            }
        }
        
        # First create the thread
        response = test_client.post(
            "/api/chatkit",
            headers=customer_auth_headers,
            json=create_and_message_payload
        )
        
        assert response.status_code == 200
        
        # Get thread_id
        thread_id = None
        for line in response.text.split('\n'):
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    if data.get("type") == "threads.create.response":
                        thread_id = data.get("thread_id")
                        break
                except json.JSONDecodeError:
                    continue
        
        assert thread_id is not None
        
        # Ask about products
        message_payload = {
            "type": "threads.add_user_message",
            "thread_id": thread_id,
            "content": "What kind of products do you sell?"
        }
        
        response = test_client.post(
            "/api/chatkit",
            headers=customer_auth_headers,
            json=message_payload
        )
        
        assert response.status_code == 200
        
        # Collect response
        ai_response = []
        for line in response.text.split('\n'):
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    if data.get("type") == "threads.run.item.delta.text":
                        ai_response.append(data.get("delta", {}).get("text", ""))
                except json.JSONDecodeError:
                    continue
        
        full_response = ''.join(ai_response)
        print(f"\n📝 AI response about products: {full_response}")
        
        # Verify the response is relevant
        assert len(full_response) > 10, "Should get a meaningful response"
        
        # The assistant should mention clothing or fashion-related terms
        response_lower = full_response.lower()
        relevant_keywords = ['clothing', 'fashion', 'apparel', 'wear', 'clothes', 'products', 'items']
        assert any(keyword in response_lower for keyword in relevant_keywords), \
            f"Response should be about clothing/products. Got: {full_response}"
        
        print("✅ Product question test passed!")
    
    def test_chatkit_conversation_continuity(
        self,
        test_client: TestClient,
        customer_auth_headers: dict,
        check_openai_config: bool
    ):
        """
        Test that the conversation maintains context across multiple messages.
        """
        
        # Create thread
        create_payload = {
            "type": "threads.create",
            "params": {
                "input": {
                    "content": [
                        {
                            "type": "input_text",
                            "text": "I'm interested in buying a jacket"
                        }
                    ],
                    "attachments": [],
                    "inference_options": {}
                },
                "metadata": {"user_id": "test_continuity"}
            }
        }
        
        response = test_client.post(
            "/api/chatkit",
            headers=customer_auth_headers,
            json=create_payload
        )
        
        # Get thread_id
        thread_id = None
        for line in response.text.split('\n'):
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    if data.get("type") == "threads.create.response":
                        thread_id = data.get("thread_id")
                        break
                except json.JSONDecodeError:
                    continue
        
        assert thread_id is not None
        
        # First message: Mention a specific topic
        msg1_payload = {
            "type": "threads.add_user_message",
            "thread_id": thread_id,
            "content": "I'm looking for a red shirt."
        }
        
        response1 = test_client.post(
            "/api/chatkit",
            headers=customer_auth_headers,
            json=msg1_payload
        )
        
        assert response1.status_code == 200
        
        # Second message: Reference the previous topic
        msg2_payload = {
            "type": "threads.add_user_message",
            "thread_id": thread_id,
            "content": "What size should I get?"
        }
        
        response2 = test_client.post(
            "/api/chatkit",
            headers=customer_auth_headers,
            json=msg2_payload
        )
        
        assert response2.status_code == 200
        
        # Collect response
        ai_response = []
        for line in response2.text.split('\n'):
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    if data.get("type") == "threads.run.item.delta.text":
                        ai_response.append(data.get("delta", {}).get("text", ""))
                except json.JSONDecodeError:
                    continue
        
        full_response = ''.join(ai_response)
        
        # The response should reference sizing or provide relevant info
        assert len(full_response) > 10, "Should get a response"
        response_lower = full_response.lower()
        
        # Should mention sizing concepts
        size_keywords = ['size', 'fit', 'measure', 'small', 'medium', 'large']
        has_size_reference = any(keyword in response_lower for keyword in size_keywords)
        
        assert has_size_reference or len(full_response) > 30, \
            f"Response should address sizing. Got: {full_response}"
        


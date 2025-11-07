import os
from locust import HttpUser, task, between
import random

TEST_INPUTS = [
    "Where is my order?",
    "Can you tell me the status of my recent order?",
    "I placed an order last week, has it shipped yet?",
    "What's the tracking number for my order?",
    "When will my order arrive?",
    "I haven't received my order yet, can you help?",
    "How can I check my order status?",
    "Is my order on the way?",
    "Can you give me an update on order #12345?",
    "I need to know when my package will be delivered",
    "Did my order ship already?",
    "What's happening with my purchase?",
    "I ordered something 3 days ago, where is it?",
    "Can you track my order for me?",
    "My order hasn't arrived, what's going on?",
    "How long does it usually take for orders to arrive?",
    "I'm waiting for an order, can you check on it?",
    "Is there any delay with my order?",
    "Can I get the delivery status of my order?",
    "When was my order shipped?",
    "I want to know about my recent purchase",
    "Can you look up my order history?",
    "What's the estimated delivery date for my order?",
    "Has my order been processed yet?",
    "I need help tracking my package",
    "Where's the item I ordered last Tuesday?",
    "Can you tell me if my order is still processing?",
    "I'm expecting a delivery, when will it come?",
    "Is my order out for delivery?",
    "Can you confirm my order was received?",
    "I want to check on the status of my shipment",
    "Has my order left the warehouse yet?",
    "When should I expect my order to arrive?",
    "I ordered multiple items, have they all shipped?",
    "Can you give me tracking information?",
    "My order is taking longer than expected, why?",
    "I need to know if my order is on schedule",
    "Has there been any update on my order?",
    "Can you tell me where my package is right now?",
    "I want to track my recent order",
    "Is my order delayed?",
    "When did you ship my order?",
    "I placed an order yesterday, can you confirm it?",
    "What's the current status of my purchase?",
    "Can you help me locate my order?",
    "I'm concerned about my order, it hasn't arrived",
    "How do I find out when my order will be delivered?",
    "Can you check if my order has been dispatched?",
    "I need an update on my order please",
    "Where can I see my order tracking details?",
]

class ChatUser(HttpUser):
    wait_time = between(2, 10)

    @task
    def chat_with_bot(self):
        # Login
        login_response = self.client.post(
            "/api/login", json={"username": "stacey", "password": os.environ.get("TEST_USER_PASSWORD", "stacey123")})
        access_token = login_response.json()['access_token']

        payload = {
            "type": "threads.create",
            "params":
            {"input":
             {"content": [
                 {"type": "input_text", "text": random.choice(TEST_INPUTS)}
             ], "quoted_text": "", "attachments": [], "inference_options": {}}
             }
        }

        result = self.client.post(
            "/api/chatkit", json=payload, headers={"Authorization": f"Bearer {access_token}"}
            )

        # logout
        self.client.post(
            "/api/logout", headers={"Authorization": f"Bearer {access_token}"}
        )

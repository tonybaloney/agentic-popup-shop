import os
from locust import HttpUser, task
import random
from datetime import datetime
import math
from zoneinfo import ZoneInfo

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
    "What are your store hours?",
    "Do you offer gift wrapping services?",
    "Can I change my password?",
    "How do I create an account on your website?",
    "What payment methods do you accept?",
    "Do you have a loyalty program?",
    "Can you tell me about your return policy?",
    "Are there any current promotions or sales?",
    "How can I contact customer support?",
    "Do you ship internationally?",
]

def peak_between(min_wait, max_wait):
    """Custom wait time function to simulate peak usage periods.

    Wait times are shorter (min_wait) at midday (12:00 PST) and longer (max_wait) at midnight (00:00 PST).
    Uses a cosine wave to smoothly transition between peak and off-peak times.
    """
    def wait_time():
        # Get current hour in US Pacific Time (0-23)
        pst_timezone = ZoneInfo("America/Los_Angeles")
        current_hour = datetime.now(pst_timezone).hour

        # Convert hour to radians (0 at midnight, π at noon, 2π at next midnight)
        # Shift by π so that cos(0) = 1 at midnight and cos(π) = -1 at noon
        hour_radians = (current_hour / 12.0) * math.pi

        # Calculate wait time using cosine wave
        # cos(0) = 1 (midnight, max wait), cos(π) = -1 (noon, min wait)
        # Normalize from [-1, 1] to [min_wait, max_wait]
        normalized_factor = (math.cos(hour_radians) + 1) / 2  # Converts to [0, 1]
        calculated_wait = min_wait + (max_wait - min_wait) * normalized_factor

        # Add some randomness (±10%) to make it more realistic
        jitter = calculated_wait * 0.1
        return random.uniform(calculated_wait - jitter, calculated_wait + jitter)

    return wait_time

class ChatUser(HttpUser):
    wait_time = peak_between(5, 60)

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

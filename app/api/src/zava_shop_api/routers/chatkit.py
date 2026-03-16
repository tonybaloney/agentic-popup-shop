"""
ChatKit router for customer AI chat functionality.
"""

from dataclasses import dataclass
import logging
import os
from datetime import datetime
from typing import AsyncIterator, Callable

from agent_framework import Agent, tool
from agent_framework_azure_ai import AzureAIClient
from agent_framework_chatkit import ThreadItemConverter, stream_agent_response
from azure.identity.aio import DefaultAzureCredential
from chatkit.server import ChatKitServer, StreamingResult
from chatkit.store import StoreItemType, default_generate_id
from chatkit.types import (
    ThreadItemDoneEvent,
    ThreadMetadata,
    ThreadStreamEvent,
    UserMessageItem,
    WidgetItem,
)
from chatkit.widgets import Button, Card, Col, Divider, Row, Spacer, Text, WidgetRoot
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from zava_shop_shared.finance_sqlite import FinanceSQLiteProvider

from zava_shop_api.memory_store import MemoryStore
from zava_shop_api.models import OrderResponse, TokenData
from zava_shop_api.openid_auth import get_current_user

from ..customers import get_customer_orders

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/chatkit", tags=["chatkit"])


@dataclass
class AssistantAgentMetadata:
    model: str
    name: str
    instructions: str

# Initialize ChatKit data store (SQLite for development)
data_store = MemoryStore()

agent_version = os.environ.get("AZURE_AI_PROJECT_AGENT_VERSION", None)
if agent_version is not None and not agent_version.strip():
    agent_version = None

chat_client = AzureAIClient(
    credential=DefaultAzureCredential(),
    agent_name=os.environ.get("AZURE_AI_PROJECT_AGENT_ID", "zava-customer-agent"),
    agent_version=agent_version,
    model_deployment_name=os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5-mini"),
)


class ChatKitContext(BaseModel):
    """Context passed to ChatKit server."""

    user_id: str
    customer_id: int | None
    role: str
    user_agent: str | None

    def __contains__(self, key: str) -> bool:
        return key in self.model_dump()

    def __getitem__(self, key: str):
        return self.model_dump()[key]


async def stream_widget(
    thread_id: str,
    widget: WidgetRoot,
    copy_text: str | None = None,
    generate_id: Callable[[StoreItemType], str] = default_generate_id,
) -> AsyncIterator[ThreadStreamEvent]:
    """Stream a ChatKit widget as a ThreadStreamEvent.
    This helper function creates a ChatKit widget item and yields it as a
    ThreadItemDoneEvent that can be consumed by the ChatKit UI.
    Args:
        thread_id: The ChatKit thread ID for the conversation.
        widget: The ChatKit widget to display.
        copy_text: Optional text representation of the widget for copy/paste.
        generate_id: Optional function to generate IDs for ChatKit items.
    Yields:
        ThreadStreamEvent: ChatKit event containing the widget.
    """
    item_id = generate_id("message")

    widget_item = WidgetItem(
        id=item_id,
        thread_id=thread_id,
        created_at=datetime.now(),
        widget=widget,
        copy_text=copy_text,
    )

    yield ThreadItemDoneEvent(type="thread.item.done", item=widget_item)


def render_order_widget(data: OrderResponse) -> WidgetRoot:
    order_rows = [
        Row(
            align="center",
            children=[
                # TODO: This renders from the openai CDN, I don't know how to override the domain
                # Image(src=f"/images/{order_item.image_url}", size=48),
                Col(
                    children=[
                        Text(value=order_item.product_name, size="md", weight="semibold", color="emphasis"),
                        Text(
                            value=f"{order_item.quantity} x ${order_item.unit_price:.2f}", size="sm", color="secondary"
                        ),
                    ]
                )
            ],
        )
        for order_item in data.items
    ]

    return Card(
        size="sm",
        children=[
            Col(children=order_rows),
            Divider(flush=True),
            Col(
                children=[
                    Row(
                        children=[
                            Text(value="Total with tax", weight="semibold", size="sm"),
                            Spacer(),
                            Text(value=f"${data.order_total:.2f}", weight="semibold", size="sm"),
                        ]
                    )
                ]
            ),
            Divider(flush=True),
            Col(
                children=[
                    Button(
                        label="Return",
                        # on_click_action=ClickAction(type="purchase"),
                        style="primary",
                        block=True,
                    )
                ]
            ),
        ],
    )


def render_return_widget(data: OrderResponse) -> WidgetRoot:
    """Render a ChatKit widget card prompting the customer to complete a return."""
    item_rows = [
        Row(
            align="center",
            children=[
                Col(
                    children=[
                        Text(value=order_item.product_name, size="md", weight="semibold", color="emphasis"),
                        Text(
                            value=f"Qty {order_item.quantity} · ${order_item.total_amount:.2f}",
                            size="sm",
                            color="secondary",
                        ),
                    ]
                )
            ],
        )
        for order_item in data.items
    ]

    return Card(
        size="sm",
        children=[
            Text(
                value=f"📦 Return — Order #{data.order_id}",
                size="lg",
                weight="bold",
                color="emphasis",
            ),
            Text(
                value=(
                    "To complete your return, click the Return button on your order in the dashboard. "
                    "For full-order returns you will need to upload a photo of the items in the box."
                ),
                size="sm",
                color="secondary",
            ),
            Divider(flush=True),
            Col(children=item_rows),
            Divider(flush=True),
            Row(
                children=[
                    Text(value="Order Total", weight="semibold", size="sm"),
                    Spacer(),
                    Text(value=f"${data.order_total:.2f}", weight="semibold", size="sm"),
                ]
            ),
        ],
    )


class ZavaShopChatKitServer(ChatKitServer):
    """Custom ChatKit server for Zava Shop customer assistance."""

    def __init__(self, data_store):
        super().__init__(data_store, attachment_store=None)

        self.client = chat_client
        self.assistant_agent = AssistantAgentMetadata(
            model="gpt-4o-mini",
            name="Zava Shop Assistant",
            instructions=(
                "You are a helpful assistant for Zava Shop customers. "
                "Provide concise answers and assist with order-related requests."
            ),
        )
        self.agent = Agent(
            client=chat_client,
            name="zava-customer-agent",
            description="AI chat assistant for Zava Shop customers",
            instructions=(
                "You are a helpful assistant for Zava Shop customers. "
                "Provide concise answers to user questions. "
                "If a customer wants to return a product or order, use the initiate_return tool "
                "to start the return process. First retrieve their orders so you know which order "
                "they are referring to, then call initiate_return with the order_id. "
                "If you don't know the answer, say 'I don't know'."
            ),
        )
        self.db_provider = FinanceSQLiteProvider()
        self.converter = ThreadItemConverter()

    async def respond(
        self,
        thread: ThreadMetadata,
        input_user_message: UserMessageItem | None,
        context: ChatKitContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Process user messages and stream AI responses."""

        agent_messages = await self.converter.to_agent_input(input_user_message)

        if not input_user_message:
            raise ValueError("No user message provided")

        orders: list[OrderResponse] = []
        return_initiated_order_id: list[int] = []

        @tool
        async def get_orders(limit: int = 5) -> dict:
            """
            You can retrieve the customer's orders by calling this function.
            Orders are already ordered by most recent first, so calling with limit=1 will return the most recent order.
            The customer is already authenticated in the chat context.
            This function returns the orders as a dictionary for the authenticated user.
            """
            await self.db_provider.create_pool()
            async with self.db_provider.get_session() as session:
                if context.customer_id is None:
                    raise ValueError("Customer ID is not available in context")

                orders_response = await get_customer_orders(
                    customer_id=context.customer_id, session=session, limit=limit
                )
                orders.extend(orders_response.orders)
                # Convert to dict for AI function return
                return orders_response.model_dump()

        @tool
        async def initiate_return(order_id: int) -> dict:
            """
            Initiate a product return for a specific order.
            Call this when the customer says they want to return a product, return an order,
            or asks about the return process. First retrieve their orders using get_orders
            to identify the correct order_id, then call this function.
            This will display a return form widget in the chat where the customer can
            choose full or partial return and upload a photo if needed.
            """
            return_initiated_order_id.append(order_id)
            return {
                "status": "return_form_displayed",
                "order_id": order_id,
                "message": (
                    f"I've opened the return form for order #{order_id}. "
                    "You can choose to return the full order or specific items. "
                    "For full-order returns, you'll need to upload a photo of the items in the box."
                ),
            }

        async for event in stream_agent_response(
            self.agent.run(agent_messages, tools=[get_orders, initiate_return], stream=True),
            thread_id=thread.id,
        ):
            yield event

        if orders:
            for order in orders:
                widget = render_order_widget(order)
                async for widget_event in stream_widget(
                    thread_id=thread.id,
                    widget=widget,
                    copy_text=f"Order #{order.order_id}: {order.total_items} from {order.store_name}, Total: ${order.order_total}",
                ):
                    yield widget_event

        # If a return was initiated, render a return form widget
        if return_initiated_order_id:
            for oid in return_initiated_order_id:
                # Find the matching order to show details
                matching = [o for o in orders if o.order_id == oid]
                if matching:
                    return_widget = render_return_widget(matching[0])
                    async for widget_event in stream_widget(
                        thread_id=thread.id,
                        widget=return_widget,
                        copy_text=f"Return initiated for Order #{oid}",
                    ):
                        yield widget_event


# Initialize server
chatkit_server = ZavaShopChatKitServer(data_store)


@router.post("")
async def chatkit_endpoint(request: Request, current_user: TokenData = Depends(get_current_user)):
    """
    Main ChatKit endpoint that handles all chat operations.
    Supports both JSON and SSE streaming responses.
    Requires authentication via Bearer token.
    """
    try:
        # Verify user has customer role
        if current_user.user_role != "customer":
            raise HTTPException(status_code=403, detail="Only customers can access this endpoint")

        # Pass user context to ChatKit
        context = ChatKitContext(
            user_id=current_user.username,
            customer_id=current_user.customer_id,
            role=current_user.user_role,
            user_agent=request.headers.get("user-agent"),
        )

        result = await chatkit_server.process(await request.body(), context)

        if isinstance(result, StreamingResult) or hasattr(result, "__aiter__"):
            return StreamingResponse(result, media_type="text/event-stream")
        else:
            response_content = result.json if hasattr(result, "json") else result
            return Response(content=response_content, media_type="application/json")

    except HTTPException:
        # Re-raise HTTP exceptions so FastAPI handles them properly
        raise
    except Exception as e:
        logger.error(f"ChatKit endpoint error: {e}", exc_info=True)
        return JSONResponse(content={"error": str(e)}, status_code=500)

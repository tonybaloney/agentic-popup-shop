"""
ChatKit router for customer AI chat functionality.
"""
from datetime import datetime
from agent_framework import ChatAgent, ai_function
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from zava_shop_api.memory_store import MemoryStore
from zava_shop_api.models import OrderResponse, TokenData
from zava_shop_api.auth import get_current_user
from chatkit.server import ChatKitServer, StreamingResult
from chatkit.types import (
    ThreadMetadata,
    ThreadItemDoneEvent,
    UserMessageItem,
    ThreadStreamEvent,
    WidgetItem,
)
from chatkit.store import StoreItemType, default_generate_id
from chatkit.actions import ActionConfig
from chatkit.widgets import Button, Card, Col, Divider, Image, Row, Text, Title, WidgetRoot, Spacer

from agent_framework_chatkit import ThreadItemConverter, stream_agent_response
import os

from typing import AsyncIterator, Callable, Optional
import logging

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/chatkit", tags=["chatkit"])

# Initialize ChatKit data store (SQLite for development)
data_store = MemoryStore()

from agent_framework.azure import AzureOpenAIChatClient
from zava_shop_shared.finance_sqlite import FinanceSQLiteProvider
from .customers import get_customer_orders

chat_client = AzureOpenAIChatClient(api_key=os.environ.get("AZURE_OPENAI_API_KEY_GPT5"),
                                    endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT_GPT5"),
                                    deployment_name=os.environ.get("AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5"),
                                    api_version=os.environ.get("AZURE_OPENAI_ENDPOINT_VERSION_GPT5", "2024-02-15-preview"))

class ChatKitContext(BaseModel):
    """Context passed to ChatKit server."""
    user_id: str
    customer_id: int | None
    role: str
    user_agent: str | None


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
                        Text(
                            value=order_item.product_name,
                            size="md",
                            weight="semibold",
                            color="emphasis"
                        ),
                        Text(
                            value=f"{order_item.quantity} x ${order_item.unit_price:.2f}",
                            size="sm",
                            color="secondary"
                        )
                    ]
                )
            ]
        )
        for order_item in data.items
    ]

    return Card(
            size="sm",
            children=[
                Col(
                    children=order_rows
                ),
                
                Divider(flush=True),
                
                Col(
                    children=[
                        Row(
                            children=[
                                Text(value="Total with tax", weight="semibold", size="sm"),
                                Spacer(),
                                Text(value=f"${data.order_total:.2f}", weight="semibold", size="sm")
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
                            block=True
                        )
                    ]
                )
            ]
        )


class ZavaShopChatKitServer(ChatKitServer):
    """Custom ChatKit server for Zava Shop customer assistance."""

    def __init__(self, data_store):
        super().__init__(data_store, attachment_store=None)

        self.client = chat_client
        self.agent = ChatAgent(
            chat_client,
            instructions=(
                "You are a helpful assistant."
                "Provide concise answers to user questions."
                "If you don't know the answer, say 'I don't know'."
            )
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

        @ai_function
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
                    customer_id=context.customer_id,
                    session=session,
                    limit=limit
                )
                orders.extend(orders_response.orders)
                # Convert to dict for AI function return
                return orders_response.model_dump()



        async for event in stream_agent_response(
                self.agent.run_stream(agent_messages, tools=[get_orders]),
                thread_id=thread.id,
            ):
                yield event

        if orders:
            for order in orders:
                widget = render_order_widget(order)
                async for widget_event in stream_widget(
                    thread_id=thread.id,
                    widget=widget,
                    copy_text=f"Order #{order.order_id}: {order.total_items} from {order.store_name}, Total: ${order.order_total}"
                ):
                    yield widget_event


# Initialize server
chatkit_server = ZavaShopChatKitServer(data_store)

@router.post("")
async def chatkit_endpoint(request: Request,
                           current_user: TokenData = Depends(get_current_user)
):
    """
    Main ChatKit endpoint that handles all chat operations.
    Supports both JSON and SSE streaming responses.
    Requires authentication via Bearer token.
    """
    try:
        # Verify user has customer role
        if current_user.user_role != "customer":
            raise HTTPException(
                status_code=403,
                detail="Only customers can access this endpoint"
            )

        # Pass user context to ChatKit
        context = ChatKitContext(
            user_id=current_user.username,
            customer_id=current_user.customer_id,
            role=current_user.user_role,
            user_agent=request.headers.get("user-agent"),
        )

        result = await chatkit_server.process(await request.body(), context)

        if isinstance(result, StreamingResult):
            return StreamingResponse(result, media_type="text/event-stream")
        else:
            return Response(content=result.json, media_type="application/json")

    except HTTPException:
        # Re-raise HTTP exceptions so FastAPI handles them properly
        raise
    except Exception as e:
        logger.error(f"ChatKit endpoint error: {e}", exc_info=True)
        return JSONResponse(
            content={"error": str(e)},
            status_code=500
        )

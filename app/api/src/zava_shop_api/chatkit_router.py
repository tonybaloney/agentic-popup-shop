"""
ChatKit router for customer AI chat functionality.
"""

from datetime import datetime
from agent_framework import ChatMessage, Role, ai_function
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from zava_shop_api.memory_store import MemoryStore
from zava_shop_api.models import OrderListResponse, TokenData
from zava_shop_api.auth import get_current_user
from chatkit.server import ChatKitServer, StreamingResult
from chatkit.types import (
    ThreadMetadata,
    UserMessageItem,
    ThreadStreamEvent,
    ThreadCreatedEvent,
    ThreadItemAddedEvent,
    ThreadItemDoneEvent,
    Thread,
    AssistantMessageItem,
    AssistantMessageContent,
    UserMessageTextContent,
    Page,
)

import os

from typing import AsyncIterator
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


class ZavaShopChatKitServer(ChatKitServer):
    """Custom ChatKit server for Zava Shop customer assistance."""

    def __init__(self, data_store):
        super().__init__(data_store, attachment_store=None)

        self.client = chat_client
        self.db_provider = FinanceSQLiteProvider()


    async def respond(
        self,
        thread: ThreadMetadata,
        input_user_message: UserMessageItem | None,
        context: ChatKitContext,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Process user messages and stream AI responses."""

        # Emit ThreadCreatedEvent
        chatkit_thread = Thread(
            id=thread.id,
            created_at=thread.created_at,
            title=thread.title,
            status=thread.status,
            metadata=thread.metadata,
            items=Page(data=[], has_more=False, after=None)
        )
        yield ThreadCreatedEvent(thread=chatkit_thread)

        if not input_user_message:
            raise ValueError("No user message provided")

        # Emit user message added event
        yield ThreadItemAddedEvent(item=input_user_message)

        user_input: list[ChatMessage] = [
            ChatMessage(role="user", text=m.text)
            for m in input_user_message.content
            if isinstance(m, UserMessageTextContent)
        ]

        # Track messages by ID as they stream in
        messages_by_id: dict[str, str] = {}
        message_created_at: dict[str, datetime] = {}
        first_chunk_per_message: set[str] = set()

        @ai_function
        async def get_orders() -> dict:
            """
            You can retrieve the customer's orders by calling this function.
            The customer is already authenticated in the chat context.
            This function returns the orders as a dictionary for the authenticated user.
            """
            await self.db_provider.create_pool()
            async with self.db_provider.get_session() as session:
                if context.customer_id is None:
                    raise ValueError("Customer ID is not available in context")

                orders_response = await get_customer_orders(
                    customer_id=context.customer_id,
                    session=session
                )
                # Convert to dict for AI function return
                return orders_response.model_dump()

        # Stream assistant responses
        async for update in self.client.get_streaming_response(user_input, tools=[get_orders]):
            if update.role == Role.ASSISTANT and update.text and update.message_id:
                msg_id = update.message_id

                # Accumulate text for this message
                if msg_id not in messages_by_id:
                    messages_by_id[msg_id] = ""
                    message_created_at[msg_id] = datetime.now()

                messages_by_id[msg_id] += update.text

                # Create/update assistant message item
                assistant_message = AssistantMessageItem(
                    id=msg_id,
                    thread_id=thread.id,
                    created_at=message_created_at[msg_id],
                    content=[
                        AssistantMessageContent(
                            text=messages_by_id[msg_id],
                            annotations=[]
                        )
                    ]
                )

                # Emit ThreadItemAdded for first chunk, ThreadItemAdded for updates
                if msg_id not in first_chunk_per_message:
                    first_chunk_per_message.add(msg_id)
                    yield ThreadItemAddedEvent(item=assistant_message)
                else:
                    # For subsequent chunks, emit as updates (still using ThreadItemAddedEvent)
                    # TODO: I think this should be ThreadItemUpdate, but that doesn't seem to behave the way I would expect
                    yield ThreadItemAddedEvent(item=assistant_message)
            else:
                logger.warning(f"Received unsupported update: {update.to_dict()}")

        # Emit ThreadItemDone for each completed message
        for msg_id, text in messages_by_id.items():
            assistant_message = AssistantMessageItem(
                id=msg_id,
                thread_id=thread.id,
                created_at=message_created_at[msg_id],
                content=[
                    AssistantMessageContent(
                        text=text,
                        annotations=[]
                    )
                ]
            )
            yield ThreadItemDoneEvent(item=assistant_message)


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

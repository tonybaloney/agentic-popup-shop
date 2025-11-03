"""
ChatKit router for customer AI chat functionality.
"""

from agent_framework import ChatAgent, ai_function
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from zava_shop_api.memory_store import MemoryStore
from zava_shop_api.models import TokenData
from zava_shop_api.auth import get_current_user
from chatkit.server import ChatKitServer, StreamingResult
from chatkit.types import (
    ThreadMetadata,
    UserMessageItem,
    ThreadStreamEvent,
)
from agent_framework_chatkit import ThreadItemConverter, stream_agent_response
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



        async for event in stream_agent_response(
                self.agent.run_stream(agent_messages, tools=[get_orders]),
                thread_id=thread.id,
            ):
                yield event



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

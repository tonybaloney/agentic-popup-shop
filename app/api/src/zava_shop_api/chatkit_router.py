"""
ChatKit router for customer AI chat functionality.
"""

from datetime import datetime
from agent_framework import ChatMessage
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from zava_shop_api.memory_store import MemoryStore
from zava_shop_api.models import TokenData
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

from typing import AsyncIterator, Any
import logging

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/chatkit", tags=["chatkit"])

# Initialize ChatKit data store (SQLite for development)
data_store = MemoryStore()

from agent_framework.azure import AzureOpenAIChatClient

chat_client = AzureOpenAIChatClient(api_key=os.environ.get("AZURE_OPENAI_API_KEY_GPT5"),
                                    endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT_GPT5"),
                                    deployment_name=os.environ.get("AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5"),
                                    api_version=os.environ.get("AZURE_OPENAI_ENDPOINT_VERSION_GPT5", "2024-02-15-preview"))



class ZavaShopChatKitServer(ChatKitServer):
    """Custom ChatKit server for Zava Shop customer assistance."""

    def __init__(self, data_store):
        super().__init__(data_store, attachment_store=None)

        self.client = chat_client


    async def respond(
        self,
        thread: ThreadMetadata,
        input_user_message: UserMessageItem | None,
        context: Any,
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

        user_input: list[ChatMessage] = [ChatMessage(role="user", text=m.text) for m in input_user_message.content if isinstance(m, UserMessageTextContent)]

        # Find and yield assistant messages (skip user messages)
        async for update in self.client.get_streaming_response(user_input, tools=[]):
            if update.role == "assistant" and update.text:
                # Create assistant message item
                assistant_message = AssistantMessageItem(
                    id=update.message_id,
                    thread_id=thread.id,
                    created_at=datetime.fromisoformat(update.created_at or ""),
                    content=[
                        AssistantMessageContent(
                            text=text_msg,
                            annotations=[]
                        )
                        for text_msg in update.text
                    ]
                )

                # Emit assistant message added
                yield ThreadItemAddedEvent(item=assistant_message)

                # Emit message done
                yield ThreadItemDoneEvent(item=assistant_message)


# Initialize server
chatkit_server = ZavaShopChatKitServer(data_store)


@router.post("/session")
async def create_chatkit_session(
    current_user: TokenData = Depends(get_current_user)
):
    """
    Create a new ChatKit session and return a client secret.
    This endpoint is called by the ChatKit frontend SDK to initialize.
    """
    try:
        # Verify user has customer role
        if current_user.user_role != "customer":
            raise HTTPException(
                status_code=403,
                detail="Only customers can access this endpoint"
            )
        
        # Create a session token/secret for the user
        # For ChatKit, this is typically a JWT or session identifier
        import secrets
        client_secret = secrets.token_urlsafe(32)
        
        # Store the session mapping (in production, use Redis or database)
        # For now, we'll return a simple token
        return {
            "client_secret": client_secret,
            "user_id": current_user.username,
            "customer_id": current_user.customer_id
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating ChatKit session: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


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
        context = {
            "user_id": current_user.username,
            "customer_id": current_user.customer_id,
            "role": current_user.user_role,
            "user_agent": request.headers.get("user-agent"),
        }

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

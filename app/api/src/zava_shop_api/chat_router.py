"""
Simple chat router for customer AI assistance.
Streams Azure AI agent responses using Server-Sent Events (SSE).
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from zava_shop_api.models import TokenData
from zava_shop_api.auth import get_current_user

from azure.ai.projects.aio import AIProjectClient
from azure.ai.agents.models import ListSortOrder
from azure.identity.aio import DefaultAzureCredential

import os
import logging
from typing import AsyncIterator

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    """Chat message request."""
    message: str
    thread_id: str | None = None


class ChatStreamEvent(BaseModel):
    """Server-sent event for chat streaming."""
    type: str
    data: dict


async def get_ai_project_client():
    """Get or create Azure AI Project client."""
    if not os.environ.get("AZURE_AIPROJECT_API_KEY") or not os.environ.get("AZURE_AIPROJECT_ENDPOINT"):
        raise ValueError("Azure AI Project configuration is missing")

    return AIProjectClient(
        credential=DefaultAzureCredential(),
        endpoint=os.environ.get("AZURE_AIPROJECT_ENDPOINT", "")
    )


async def stream_agent_response(
    message: str,
    thread_id: str | None,
    user_id: str
) -> AsyncIterator[str]:
    """
    Stream Azure AI agent responses as Server-Sent Events.
    
    Yields events:
    - thread_created: When a new thread is created
    - user_message: Echo of user's message
    - assistant_message_start: Assistant starts responding
    - assistant_message_chunk: Chunks of assistant response
    - assistant_message_end: Assistant finishes responding
    - error: If something goes wrong
    """
    project = None
    azure_thread = None

    try:
        # Initialize Azure AI Project client
        project = await get_ai_project_client()

        # Get the agent
        agent_id = os.environ.get("AZURE_AIPROJECT_AGENT_ID")
        if not agent_id:
            raise ValueError("AZURE_AIPROJECT_AGENT_ID not configured")

        agent = await project.agents.get_agent(agent_id)

        # Create or use existing thread
        if thread_id:
            # TODO: In production, validate user owns this thread
            azure_thread = await project.agents.threads.get(thread_id)
            logger.info(f"Using existing thread: {thread_id}")
        else:
            azure_thread = await project.agents.threads.create()
            logger.info(f"Created new thread: {azure_thread.id}")

            # Notify client of new thread
            event = ChatStreamEvent(
                type="thread_created",
                data={"thread_id": azure_thread.id}
            )
            yield f"data: {event.model_dump_json()}\n\n"
        
        # Echo user message
        event = ChatStreamEvent(
            type="user_message",
            data={"message": message}
        )
        yield f"data: {event.model_dump_json()}\n\n"
        
        # Add user message to thread
        await project.agents.messages.create(
            thread_id=azure_thread.id,
            role="user",
            content=message
        )
        
        # Run the agent
        logger.info(f"Running agent on thread {azure_thread.id}")
        event = ChatStreamEvent(
            type="assistant_message_start",
            data={}
        )
        yield f"data: {event.model_dump_json()}\n\n"
        
        run = await project.agents.runs.create_and_process(
            thread_id=azure_thread.id,
            agent_id=agent.id
        )
        
        if run.status == "failed":
            error_msg = str(run.last_error) if run.last_error else "Unknown error"
            logger.error(f"Agent run failed: {error_msg}")
            event = ChatStreamEvent(
                type="error",
                data={"message": f"Agent failed: {error_msg}"}
            )
            yield f"data: {event.model_dump_json()}\n\n"
            return
        
        # Get assistant messages
        messages = await project.agents.messages.list(
            thread_id=azure_thread.id,
            order=ListSortOrder.DESCENDING,
            limit=1
        )
        
        # Stream the assistant's response
        for msg in messages:
            if msg.role == "assistant" and msg.text_messages:
                for text_msg in msg.text_messages:
                    response_text = text_msg.text.value
                    
                    # Stream response in chunks for better UX
                    chunk_size = 50  # characters per chunk
                    for i in range(0, len(response_text), chunk_size):
                        chunk = response_text[i:i + chunk_size]
                        event = ChatStreamEvent(
                            type="assistant_message_chunk",
                            data={"chunk": chunk}
                        )
                        yield f"data: {event.model_dump_json()}\n\n"
                    
                    # Signal end of message
                    event = ChatStreamEvent(
                        type="assistant_message_end",
                        data={"message": response_text}
                    )
                    yield f"data: {event.model_dump_json()}\n\n"
                    
                    logger.info(
                        f"Assistant response: {response_text[:100]}..."
                    )
                    break
    
    except Exception as e:
        logger.error(f"Error in chat stream: {e}", exc_info=True)
        event = ChatStreamEvent(
            type="error",
            data={"message": str(e)}
        )
        yield f"data: {event.model_dump_json()}\n\n"
    
    finally:
        # Cleanup
        if project:
            await project.close()


@router.post("/stream")
async def chat_stream(
    chat_message: ChatMessage,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Stream chat responses from Azure AI agent.
    
    Returns Server-Sent Events (SSE) stream with:
    - thread_created: New thread ID
    - user_message: Echo of user's message
    - assistant_message_start: Assistant starts responding
    - assistant_message_chunk: Chunks of response text
    - assistant_message_end: Complete response
    - error: Error messages
    """
    # Only customers can chat
    if current_user.user_role != "customer":
        raise HTTPException(
            status_code=403,
            detail="Only customers can access chat"
        )
    
    logger.info(
        f"Chat request from user {current_user.username}: {chat_message.message[:50]}..."
    )
    
    return StreamingResponse(
        stream_agent_response(
            message=chat_message.message,
            thread_id=chat_message.thread_id,
            user_id=current_user.username
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

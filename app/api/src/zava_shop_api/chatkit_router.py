"""
ChatKit router for customer AI chat functionality.
Separate from main API to keep code clean and modular.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse, JSONResponse
from zava_shop_api.memory_store import MemoryStore
from zava_shop_api.models import TokenData
from zava_shop_api.auth import get_current_user
from chatkit.server import ChatKitServer, ThreadStreamEvent
from chatkit.agents import AgentContext, stream_agent_response, simple_to_agent_input
from chatkit.types import ThreadMetadata, UserMessageItem
from agents import Agent, Runner

from typing import AsyncIterator, Any
import logging

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/chatkit", tags=["chatkit"])

# Initialize ChatKit data store (SQLite for development)
data_store = MemoryStore()


class ZavaShopChatKitServer(ChatKitServer):
    """Custom ChatKit server for Zava Shop customer assistance."""
    
    def __init__(self, data_store):
        super().__init__(data_store, attachment_store=None)
        
        # Define the assistant agent
        self.assistant_agent = Agent[AgentContext](
            model="gpt-4o-mini",
            name="Zava Shop Assistant",
            instructions="""You are a helpful AI shopping assistant for Zava Shop, 
a popup clothing store. You can help customers with:

- Product recommendations and information
- Order status and history
- Store locations and hours
- General shopping assistance
- Returns and exchanges

Be friendly, concise, and helpful. Keep responses short and conversational."""
        )
    
    async def respond(
        self,
        thread: ThreadMetadata,
        input_user_message: UserMessageItem | None,
        context: Any,
    ) -> AsyncIterator[ThreadStreamEvent]:
        """Process user messages and stream AI responses."""
        
        # Create agent context
        agent_context = AgentContext(
            thread=thread,
            store=self.store,
            request_context=context,
        )
        
        # Convert user input to agent format
        agent_input = await simple_to_agent_input(input_user_message) if input_user_message else []
        
        # Run the agent and stream responses
        result = Runner.run_streamed(
            self.assistant_agent,
            agent_input,
            context=agent_context,
        )
        
        # Stream agent response events to ChatKit UI
        async for event in stream_agent_response(agent_context, result):
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
        context = {
            "user_id": current_user.username,
            "customer_id": current_user.customer_id,
            "role": current_user.user_role,
            "user_agent": request.headers.get("user-agent"),
        }
        
        # Process the request
        result = await chatkit_server.process(await request.body(), context)
        
        # Return streaming or JSON response based on result type
        if hasattr(result, '__aiter__'):  # Streaming result
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

"""
Marketing Campaign Workflow Router

FastAPI router for the marketing campaign workflow with WebSocket streaming.
Handles workflow execution, HITL approvals, and media asset serving.
"""

import base64
import json
import logging
import os
import re
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from zava_shop_agents.marketing import LocalizationResponseEvent, MarketSelectionQuestionEvent, PublishingScheduleResponseEvent, get_workflow, CampaignPlannerResponseEvent, CreativeAssetsGeneratedEvent

from agent_framework import AgentRunUpdateEvent, ChatMessage
from agent_framework import (
    RequestInfoEvent,
    ExecutorFailedEvent,
    WorkflowStatusEvent,
    WorkflowRunState,
    AgentExecutorResponse,
)
# Configure logging
logger = logging.getLogger(__name__)

# Create routers
router = APIRouter(prefix="/api/marketing", tags=["marketing"])
ws_router = APIRouter(tags=["marketing-websocket"])

# Store active WebSocket connections
active_connections: List[WebSocket] = []

# Store conversation history
conversation_history: List[Dict[str, Any]] = []

# Store pending workflow requests (from RequestInfoEvent)
pending_requests: Dict[str, Any] = {
    'request_id': None,
    'entity_id': None,
    'is_pending': False,
    'request_data': None,
    'request_type': None,
}

# Track if we're waiting for campaign planner to gather more info
waiting_for_campaign_info = False

# Store the workflow instance
workflow_instance = None


def convert_file_to_data_uri(file_path: str) -> str:
    """Convert a file:// URL to a base64 data URI for browser display."""
    if file_path.startswith("file://"):
        file_path = file_path.replace("file://", "")

    path = Path(file_path)
    if not path.exists():
        logger.warning(f"Image file not found: {file_path}")
        return (
            "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
            "width='400' height='400'%3E%3Crect width='400' height='400' "
            "fill='%23ffcccc'/%3E%3Ctext x='50%25' y='50%25' "
            "dominant-baseline='middle' text-anchor='middle' "
            "font-family='Arial' font-size='16' fill='%23cc0000'%3E"
            "Image Not Found%3C/text%3E%3C/svg%3E"
        )

    try:
        with open(path, "rb") as f:
            image_data = f.read()

        ext = path.suffix.lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        mime_type = mime_types.get(ext, 'image/png')

        b64_data = base64.b64encode(image_data).decode('utf-8')
        data_uri = f"data:{mime_type};base64,{b64_data}"

        logger.info(
            f"Converted {path.name} to data URI ({len(b64_data)} chars)")
        return data_uri

    except Exception as e:
        logger.error(f"Error converting image to data URI: {e}")
        return (
            "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
            "width='400' height='400'%3E%3Crect width='400' height='400' "
            "fill='%23ffcccc'/%3E%3Ctext x='50%25' y='50%25' "
            "dominant-baseline='middle' text-anchor='middle' "
            "font-family='Arial' font-size='16' fill='%23cc0000'%3E"
            "Error Loading Image%3C/text%3E%3C/svg%3E"
        )

# TODO: Connect this to Campaign Brief pane


def _format_campaign_plan(plan_data: Dict[str, Any]) -> str:
    """Format CampaignPlan data as markdown for the Campaign Brief pane."""
    lines = []
    lines.append("# 📋 Campaign Plan\n")

    if 'campaign_name' in plan_data:
        lines.append(f"**Campaign:** {plan_data['campaign_name']}\n")

    if 'target_audience' in plan_data:
        lines.append(f"**Target Audience:** {plan_data['target_audience']}\n")

    if 'key_message' in plan_data:
        lines.append(f"**Key Message:** {plan_data['key_message']}\n")

    if 'channels' in plan_data and plan_data['channels']:
        lines.append(f"\n**Channels:** {', '.join(plan_data['channels'])}\n")

    if 'posting_schedule' in plan_data:
        lines.append(
            f"\n**Posting Schedule:**\n{plan_data['posting_schedule']}\n")

    if 'budget_allocation' in plan_data:
        lines.append(f"\n**Budget:** {plan_data['budget_allocation']}\n")

    return '\n'.join(lines)


def _extract_media_assets(creative_data: Dict[str, Any]) -> list:
    """Extract media assets from CreativePackage data."""
    media_assets = []

    creatives = creative_data.get('creatives', [])
    logger.debug(f"Found {len(creatives)} creatives in data")

    for idx, creative in enumerate(creatives):
        # Handle both dict and object formats
        if hasattr(creative, 'model_dump'):
            creative_dict = creative.model_dump()
        elif hasattr(creative, '__dict__'):
            creative_dict = vars(creative)
        else:
            creative_dict = creative

        image_path = creative_dict.get('image_path', '')
        caption = creative_dict.get('caption', '')
        hashtags = creative_dict.get('hashtags', [])
        version = creative_dict.get('version', idx + 1)

        if image_path:
            filename = os.path.basename(image_path)

            media_asset = {
                'type': 'image',
                'url': f'http://localhost:8091/api/marketing/images/{filename}',
                'caption': caption or f'Version {version}',
                'hashtags': hashtags,
                'version': version,
                'path': image_path
            }
            media_assets.append(media_asset)
            logger.info(f"Added media asset {len(media_assets)}: {filename}")
        else:
            logger.warning(f"Skipping creative {idx+1} - no image_path")

    return media_assets


async def _broadcast(message: Dict[str, Any]):
    """Broadcast a message to all connected WebSocket clients."""
    disconnected = []
    for ws in active_connections:
        try:
            await ws.send_json(message)
        except Exception as e:
            logger.error(f"Error broadcasting to WebSocket: {e}")
            disconnected.append(ws)

    for ws in disconnected:
        if ws in active_connections:
            active_connections.remove(ws)


async def _process_agent_framework_event(event):
    """Process Agent Framework event objects from run_stream()."""

    global pending_requests
    global waiting_for_campaign_info

    # Check for custom events by class name
    event_type_name = type(event).__name__
    logger.info(f"Processing event: {event_type_name}")

    if isinstance(event, CampaignPlannerResponseEvent):
        logger.info("Campaign Planner Response Event received")
        response_text = event.response_text

        try:
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```'):
                lines = cleaned_text.split('\n')
                cleaned_text = '\n'.join(
                    lines[1:-1] if len(lines) > 2 else lines)

            response_data = json.loads(cleaned_text)
            agent_response = response_data.get('agent_response', '')
            final_plan = response_data.get('final_plan', False)
            campaign_title = response_data.get('campaign_title', '')

            if final_plan:
                # Send to campaign brief window
                await _broadcast({
                    'type': 'campaign_data',
                    'content': campaign_title,
                    'timestamp': datetime.now().isoformat(),
                    'campaign_data': {
                        'brief': agent_response,
                        'isFormattedBrief': True
                    }
                })
            else:
                # Follow-up question - send to chat
                await _broadcast({
                    'type': 'assistant',
                    'content': agent_response,
                    'timestamp': datetime.now().isoformat(),
                    'awaiting_input': True
                })
        except json.JSONDecodeError as e:
            logger.warning(f"Campaign planner response is not valid JSON: {e}")
            await _broadcast({
                'type': 'assistant',
                'content': response_text,
                'timestamp': datetime.now().isoformat(),
                'awaiting_input': True
            })
        return

    elif isinstance(event, CreativeAssetsGeneratedEvent):
        logger.info(f"Creative Assets Generated: {len(event.assets)} assets")
        return

    elif isinstance(event, MarketSelectionQuestionEvent):
        question_text = event.question_text

        await _broadcast({
            'type': 'workflow',
            'content': question_text,
            'timestamp': datetime.now().isoformat(),
            'sender': 'workflow',
            'agent_name': 'Localization Agent'
        })

        await _broadcast({
            'type': 'campaign_data',
            'timestamp': datetime.now().isoformat(),
            'campaign_data': {
                'needsCreativeApproval': False
            }
        })
        return

    elif isinstance(event, LocalizationResponseEvent):
        logger.info("Localization Response Event received")
        response_text = event.response_text

        try:
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```'):
                lines = cleaned_text.split('\n')
                cleaned_text = '\n'.join(
                    lines[1:-1] if len(lines) > 2 else lines)

            translations = json.loads(cleaned_text)

            localizations = []
            # Process translations and combine with media assets if available
            # (Implementation details omitted for brevity)

            await _broadcast({
                'type': 'campaign_data',
                'content': f'Localized {len(localizations)} items',
                'timestamp': datetime.now().isoformat(),
                'campaign_data': {
                    'localizations': localizations
                }
            })
        except json.JSONDecodeError as e:
            logger.warning(f"Localization response is not valid JSON: {e}")
            await _broadcast({
                'type': 'assistant',
                'content': response_text,
                'timestamp': datetime.now().isoformat()
            })
        return

    elif isinstance(event, PublishingScheduleResponseEvent):
        logger.info("Publishing Schedule Response Event received")
        response_text = event.response_text

        try:
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```'):
                lines = cleaned_text.split('\n')
                cleaned_text = '\n'.join(
                    lines[1:-1] if len(lines) > 2 else lines)

            schedule_items = json.loads(cleaned_text)

            await _broadcast({
                'type': 'campaign_data',
                'content': f'Generated schedule with {len(schedule_items)} items',
                'timestamp': datetime.now().isoformat(),
                'campaign_data': {
                    'schedule': schedule_items
                }
            })
        except json.JSONDecodeError as e:
            logger.warning(f"Schedule response is not valid JSON: {e}")
            await _broadcast({
                'type': 'assistant',
                'content': response_text,
                'timestamp': datetime.now().isoformat()
            })
        return

    # Handle standard Agent Framework events
    elif isinstance(event, AgentExecutorResponse):
        executor_name = event.executor_id.replace('_', ' ').title()
        agent_text = (
            event.agent_run_response.text
            if hasattr(event.agent_run_response, 'text')
            else str(event.agent_run_response)
        )

        await _broadcast({
            'type': 'assistant',
            'content': f"**{executor_name}:**\n\n{agent_text}",
            'timestamp': datetime.now().isoformat()
        })

    # TODO: This will be noisy, only use for debugging
    elif isinstance(event, AgentRunUpdateEvent):
        executor_name = event.executor_id.replace('_', ' ').title()
        update_text = event.data

        await _broadcast({
            'type': 'assistant',
            'content': f"**{executor_name} Update:**\n\n{update_text}",
            'timestamp': datetime.now().isoformat(),
            'debug': True
        })

    elif isinstance(event, RequestInfoEvent):
        pending_requests['is_pending'] = True
        pending_requests['request_id'] = event.request_id
        pending_requests['request_data'] = event.data

        # Handle different request types based on their attributes
        from zava_shop_agents.marketing import CampaignFollowupRequest, DraftFeedbackRequest, MarketSelectionRequest, ScheduleApprovalRequest

        if isinstance(event.data, CampaignFollowupRequest):
            pending_requests['request_type'] = 'campaign_followup'

            questions_text = getattr(event.data, 'questions', '')
            prompt_text = getattr(event.data, 'prompt', '')

            await _broadcast({
                'type': 'campaign_followup_required',
                'request_id': event.request_id,
                'prompt': prompt_text,
                'questions': questions_text
            })

        elif isinstance(event.data, DraftFeedbackRequest):
            pending_requests['request_type'] = 'draft_feedback'

            draft_text = getattr(event.data, 'draft_text', '')
            prompt_text = getattr(event.data, 'prompt', '')

            await _broadcast({
                'type': 'creative_approval_required',
                'request_id': event.request_id,
                'prompt': prompt_text,
                'draft': draft_text
            })

        elif isinstance(event.data, MarketSelectionRequest):
            pending_requests['request_type'] = 'market_selection'

            prompt_text = getattr(event.data, 'prompt', '')

            await _broadcast({
                'type': 'market_selection_required',
                'request_id': event.request_id,
                'prompt': prompt_text
            })

        elif isinstance(event.data, ScheduleApprovalRequest):
            pending_requests['request_type'] = 'schedule_approval'

            schedule_text = getattr(event.data, 'schedule_text', '')
            prompt_text = getattr(event.data, 'prompt', '')

            await _broadcast({
                'type': 'schedule_approval_required',
                'request_id': event.request_id,
                'prompt': prompt_text,
                'schedule': schedule_text
            })
        else:
            # Fallback for unknown request types
            logger.warning(f"Unknown request type: {type(event.data)}")
            await _broadcast({
                'type': 'unknown_request',
                'request_id': event.request_id,
                'data': str(event.data)
            })

    elif isinstance(event, ExecutorFailedEvent):
        await _broadcast({
            'type': 'system',
            'content': f"❌ Error in {event.executor_id}: {event.details}"
        })

    # Handle ExecutorInvokedEvent to show loading states
    elif 'ExecutorInvokedEvent' in event_type_name or 'Invoked' in event_type_name:
        if hasattr(event, 'executor_id'):
            executor_name = event.executor_id.replace('_', ' ').title()
            await _broadcast({
                'type': 'system',
                'content': f"{executor_name} is running...",
                'timestamp': datetime.now().isoformat(),
                'debug': True
            })

    elif isinstance(event, WorkflowStatusEvent):
        if event.state == WorkflowRunState.IDLE_WITH_PENDING_REQUESTS:
            logger.info("Workflow paused - waiting for human input")
        elif event.state == WorkflowRunState.IDLE:
            if not pending_requests['is_pending']:
                await _broadcast({
                    'type': 'system',
                    'content': '✅ Workflow completed!',
                    'timestamp': datetime.now().isoformat()
                })
    else:
        logger.warning(f"Unhandled event type: {event_type_name}")
        await _broadcast({
            'type': 'system',
            'content': f"Unhandled event type: {event_type_name}",
            'timestamp': datetime.now().isoformat(),
            'debug': True
        })


async def _send_to_workflow(content: str):
    """Send user message to the workflow by running it directly."""
    global workflow_instance, pending_requests
    try:
        if pending_requests['is_pending'] and pending_requests['request_id']:
            logger.info(
                f"Responding to HITL request: {pending_requests['request_id']}")

            old_request_id = pending_requests['request_id']
            responses = {old_request_id: content}

            async for event in workflow_instance.send_responses_streaming(responses):
                await _process_agent_framework_event(event)

            if pending_requests['request_id'] == old_request_id:
                pending_requests['is_pending'] = False
                pending_requests['request_id'] = None
                pending_requests['request_data'] = None

            return

        # Start new workflow run
        global waiting_for_campaign_info
        waiting_for_campaign_info = False

        logger.info("Starting new workflow")

        start_message = {
            'type': 'system',
            'content': 'Starting Marketing Campaign Workflow...',
            'timestamp': datetime.now().isoformat()
        }
        conversation_history.append(start_message)
        await _broadcast(start_message)

        message = ChatMessage(role="user", text=content)

        async for event in workflow_instance.run_stream(message):
            await _process_agent_framework_event(event)

    except Exception as e:
        logger.error(f"Error in _send_to_workflow: {e}")

        error_message = {
            'type': 'error',
            'content': f'Failed to send message to workflow: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }
        conversation_history.append(error_message)
        await _broadcast(error_message)

        traceback.print_exc()
        raise


async def process_user_input(content: str):
    """Process user input and send to workflow."""
    if not content:
        return

    user_message = {
        'type': 'user',
        'content': content,
        'timestamp': datetime.now().isoformat()
    }
    conversation_history.append(user_message)
    await _broadcast(user_message)

    try:
        await _send_to_workflow(content)
    except Exception as e:
        logger.exception("Failed to process user input", exc_info=e)
        error_message = {
            'type': 'error',
            'content': f'Failed to send message to workflow: {str(e)}',
            'timestamp': datetime.now().isoformat()
        }
        conversation_history.append(error_message)
        await _broadcast(error_message)


# Initialize workflow on startup
def init_workflow():
    """Initialize the workflow instance."""
    global workflow_instance
    workflow_instance = get_workflow()


# WebSocket route on the separate router
@ws_router.websocket("/ws/marketing/campaign")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication."""
    await websocket.accept()
    active_connections.append(websocket)

    await websocket.send_json({
        'type': 'system',
        'content': 'Connected to Marketing Campaign Workflow',
        'timestamp': datetime.now().isoformat()
    })

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)

            if message_data.get('type') == 'message':
                content = message_data.get('content', '').strip()
                if content:
                    await process_user_input(content)

    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)


@router.post("/message")
async def handle_message(data: Dict[str, Any]):
    """Handle incoming messages via HTTP POST."""
    content = data.get('content', '').strip()

    if content:
        await process_user_input(content)
        return JSONResponse({'status': 'success'})

    return JSONResponse(
        {'status': 'error', 'message': 'No content provided'},
        status_code=400
    )


@router.get("/history")
async def get_history():
    """Get conversation history."""
    return JSONResponse(conversation_history)


@router.get("/status")
async def check_workflow_status():
    """Check if the workflow is available."""
    try:
        global workflow_instance
        if workflow_instance is not None:
            return JSONResponse({'status': 'online', 'mode': 'direct'})
        else:
            return JSONResponse(
                {'status': 'offline', 'message': 'Workflow not initialized'},
                status_code=503
            )
    except Exception as e:
        return JSONResponse(
            {'status': 'error', 'message': str(e)},
            status_code=503
        )


@router.get("/images/{filename}")
async def serve_image(filename: str):
    """Serve generated images from the generated_images folder."""
    if not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Construct path to generated image
    image_path = Path(__file__).parent.parent.parent.parent.parent / \
        'generated_images' / filename

    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(image_path)


# Initialize workflow when module is imported
init_workflow()

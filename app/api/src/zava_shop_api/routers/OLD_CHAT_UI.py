#!/usr/bin/env python3
"""
Custom Chat UI for Marketing Campaign Workflow

This chat interface runs the workflow directly (no DevUI dependency) and streams
events to a React frontend via WebSocket.
"""

from agent_framework import ChatMessage
import importlib.util
from dotenv import load_dotenv
from aiohttp.web_ws import WebSocketResponse
from aiohttp import web, WSMsgType
from typing import Dict, List, Any
from pathlib import Path
from datetime import datetime
import logging
import json
import base64
import asyncio
import os

# Disable OpenTelemetry completely
os.environ["OTEL_SDK_DISABLED"] = "true"


# Import the workflow directly
# UPDATED: Using marketing-workflow.py with creative tools and localization
spec = importlib.util.spec_from_file_location(
    "marketing_workflow", "marketing-workflow.py")
marketing_workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(marketing_workflow)
get_workflow = marketing_workflow.get_workflow


# Configure logging
logging.basicConfig(level=logging.INFO)

# Store active WebSocket connections
active_connections: List[WebSocketResponse] = []
# Store conversation history
conversation_history: List[Dict[str, Any]] = []
# Store pending workflow requests (from RequestInfoEvent)
pending_requests: Dict[str, Any] = {
    'request_id': None,
    'entity_id': None,
    'is_pending': False,
    'request_data': None,
    # Track the type of HITL request (campaign_plan, creative_package, etc.)
    'request_type': None
}
# Track if we're waiting for campaign planner to gather more info
waiting_for_campaign_info = False
# Store the workflow instance
workflow_instance = None


def convert_file_to_data_uri(file_path: str) -> str:
    """Convert a file:// URL to a base64 data URI for browser display."""
    # Handle file:// URLs
    if file_path.startswith("file://"):
        file_path = file_path.replace("file://", "")

    # Check if file exists
    path = Path(file_path)
    if not path.exists():
        print(f"⚠️ Image file not found: {file_path}")
        return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='400'%3E%3Crect width='400' height='400' fill='%23ffcccc'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-family='Arial' font-size='16' fill='%23cc0000'%3EImage Not Found%3C/text%3E%3C/svg%3E"

    try:
        # Read image file and convert to base64
        with open(path, "rb") as f:
            image_data = f.read()

        # Determine MIME type based on extension
        ext = path.suffix.lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        mime_type = mime_types.get(ext, 'image/png')

        # Create data URI
        b64_data = base64.b64encode(image_data).decode('utf-8')
        data_uri = f"data:{mime_type};base64,{b64_data}"

        print(f"✅ Converted {path.name} to data URI ({len(b64_data)} chars)")
        return data_uri

    except Exception as e:
        print(f"❌ Error converting image to data URI: {e}")
        return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='400'%3E%3Crect width='400' height='400' fill='%23ffcccc'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-family='Arial' font-size='16' fill='%23cc0000'%3EError Loading Image%3C/text%3E%3C/svg%3E"


class ChatUIServer:
    """Custom chat UI server that runs the workflow directly."""

    def __init__(self):
        self.app = web.Application()
        self._setup_routes()
        global workflow_instance
        workflow_instance = get_workflow()

    def _setup_routes(self):
        """Setup all routes for the chat UI server."""
        self.app.router.add_get('/ws', self.websocket_handler)
        self.app.router.add_post('/api/message', self.handle_message)
        self.app.router.add_get('/api/history', self.get_history)
        self.app.router.add_get('/api/status', self.check_workflow_status)
        self.app.router.add_get('/images/{filename}', self.serve_image)

    async def websocket_handler(self, request: web.Request) -> WebSocketResponse:
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        active_connections.append(ws)

        # Send welcome message
        await ws.send_json({
            'type': 'system',
            'content': 'Connected to Marketing Campaign Workflow Chat UI',
            'timestamp': datetime.now().isoformat()
        })

        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self.process_user_input(data.get('content', ''))
                    except json.JSONDecodeError:
                        await ws.send_json({'error': 'Invalid JSON', 'type': 'error'})
                elif msg.type == WSMsgType.ERROR:
                    print(f'WebSocket error: {ws.exception()}')
        finally:
            if ws in active_connections:
                active_connections.remove(ws)

        return ws

    async def process_user_input(self, content: str):
        """Process user input, send to workflow, and broadcast responses."""
        if not content:
            return

        # Add user message to history and broadcast
        user_message = {
            'type': 'user',
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        conversation_history.append(user_message)
        await self._broadcast(user_message)

        # Send message to workflow via HTTP
        try:
            await self._send_to_workflow(content)
        except Exception as e:
            error_message = {
                'type': 'error',
                'content': f'Failed to send message to workflow: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
            conversation_history.append(error_message)
            await self._broadcast(error_message)

    async def _send_to_workflow(self, content: str):
        """Send user message to the workflow by running it directly."""
        try:
            global workflow_instance, pending_requests

            # DEBUG: Log pending_requests state
            print(
                f"\n🔍 DEBUG _send_to_workflow called with content: '{content}'")
            print(
                f"🔍 DEBUG pending_requests['is_pending']: {pending_requests['is_pending']}")
            print(
                f"🔍 DEBUG pending_requests['request_id']: {pending_requests['request_id']}")
            print(f"🔍 DEBUG Full pending_requests: {pending_requests}")

            # Check if we have a pending request that needs a response
            if pending_requests['is_pending'] and pending_requests['request_id']:
                print("\n" + "="*60)
                print(f"🔄 RESPONDING TO HITL REQUEST")
                print("="*60)
                print(f"Request ID: {pending_requests['request_id']}")
                print(f"User Response: {content}")
                print(
                    f"Request Type: {pending_requests.get('request_type', 'UNKNOWN')}")
                print("="*60)

                # Send response to resume the workflow
                # Format: {request_id: response_string}
                old_request_id = pending_requests['request_id']
                responses = {old_request_id: content}
                print(
                    f"🔍 DEBUG Calling send_responses_streaming with: {responses}")

                # Track if this is a creative or localization approval that should route through gateway
                request_type = pending_requests.get('request_type')
                print(f"🔍 DEBUG Request type: {request_type}")

                async for event in workflow_instance.send_responses_streaming(responses):
                    # print(f"🔍 DEBUG Got event from send_responses_streaming: {type(event).__name__}")
                    await self._process_agent_framework_event(event)

                # Only clear pending request if a new one wasn't created during the response stream
                # (e.g., dual HITL: campaign approval triggers creative generation which creates new HITL request)
                if pending_requests['request_id'] == old_request_id:
                    # No new request was created, safe to clear
                    pending_requests['is_pending'] = False
                    pending_requests['request_id'] = None
                    pending_requests['entity_id'] = None
                    print("✅ Response sent to workflow - no new pending requests")
                else:
                    # A new pending request was created during the stream, keep it
                    print(
                        f"✅ Response sent to workflow - new pending request detected: {pending_requests['request_id']}")

                return

            # Start new workflow run
            global waiting_for_campaign_info
            waiting_for_campaign_info = False  # Reset flag for new workflow

            print("\n" + "="*60)
            print(f"📤 STARTING NEW WORKFLOW")
            print("="*60)
            print(f"User Input: {content}")
            print("="*60)

            # Send workflow started message to chat
            start_message = {
                'type': 'system',
                'content': 'Starting Marketing Campaign Workflow...',
                'timestamp': datetime.now().isoformat()
            }
            conversation_history.append(start_message)
            await self._broadcast(start_message)

            # Create the input message
            message = ChatMessage(role="user", text=content)

            print(f"✅ Running workflow with message...")

            # Run the workflow and stream events
            async for event in workflow_instance.run_stream(message):
                await self._process_agent_framework_event(event)

            # Note: Completion message is now handled in WorkflowStatusEvent processing
            # to avoid showing "completed" when workflow is just paused for HITL

        except Exception as e:
            print(f"❌ Error in _send_to_workflow: {e}")
            import traceback
            traceback.print_exc()
            raise

    # DEPRECATED: session: aiohttp.ClientSession
    async def _start_new_workflow(self, session, entity_id: str, content: str):
        """Start a new workflow run."""
        # API expects input as a simple string
        payload = {
            "model": entity_id,
            "input": content,
            "extra_body": {
                "entity_id": entity_id
            }
        }

        print("\n" + "="*60)
        print(f"📤 STARTING NEW WORKFLOW (DEPRECATED PATH)")
        print("="*60)
        print(f"Entity ID: {entity_id}")
        print(f"User Input: {content}")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        print("="*60)

        # NOTE: Message already sent by _send_to_workflow, don't duplicate

        # Send campaign brief loading indicator (if not already sent)
        brief_loading_message = {
            'type': 'campaign_data',
            'content': 'Creating your campaign brief...',
            'timestamp': datetime.now().isoformat(),
            'campaign_data': {
                'brief': '',  # Empty brief triggers loading spinner
                'isFormattedBrief': False,
                'isLoading': True
            }
        }
        await self._broadcast(brief_loading_message)

        # For workflows with streaming, call the workflow's run method directly via HTTP
        # Use the same approach as the original working code
        await self._call_workflow_via_python(session, entity_id, content)

    # DEPRECATED: session: aiohttp.ClientSession
    async def _call_workflow_via_python(self, session, entity_id: str, user_input: str):
        """Call the workflow directly in Python - no HTTP needed!"""
        print(f"\n🐍 CALLING WORKFLOW DIRECTLY IN PYTHON")
        print(f"Entity ID: {entity_id}")
        print(f"Input: {user_input[:200]}...")

        try:
            # Import the workflow
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "marketing_workflow", "marketing-workflow.py")
            marketing_workflow = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(marketing_workflow)
            get_workflow = marketing_workflow.get_workflow
            from agent_framework import ChatMessage

            # Get the workflow instance
            workflow = get_workflow()

            # Create the input message
            message = ChatMessage(role="user", text=user_input)

            print(f"✅ Workflow loaded, starting execution...")

            # Run the workflow and stream events
            async for event in workflow.run_stream(message):
                event_type = type(event).__name__
                print(f"\n📨 Workflow event: {event_type}")

                # Log ALL event attributes for debugging
                if hasattr(event, '__dict__'):
                    attrs = {k: v for k, v in event.__dict__.items()
                             if not k.startswith('_')}
                    print(f"   Attributes: {list(attrs.keys())}")
                    for key, value in attrs.items():
                        if value is not None and str(value).strip():
                            print(f"   {key}: {str(value)[:200]}")

                # REMOVED: ChatMessage heuristic detection (unreliable - doesn't check final_plan)
                # Campaign brief is now ONLY sent via CampaignPlannerResponseEvent with final_plan=true

                # Handle ExecutorInvokedEvent - show which executor is running
                if event_type == 'ExecutorInvokedEvent':
                    executor_id = getattr(event, 'executor_id', 'unknown')
                    print(f"🔧 Executor started: {executor_id}")

                    # Map executor IDs to user-friendly names
                    agent_names = {
                        'campaign_planner_agent': 'Campaign Planner',
                        'creative_agent': 'Creative Director',
                        'localization_agent': 'Localization Specialist',
                        'publishing_agent': 'Publishing Scheduler',
                        'hitl_review': 'Awaiting Your Review',
                        'final_hitl_approval': 'Final Review',
                    }

                    # Only show messages for actual agents (skip coordinator)
                    if executor_id in agent_names:
                        executor_name = agent_names[executor_id]
                        executor_message = {
                            'type': 'system',
                            'content': f"{executor_name} is working...",
                            'timestamp': datetime.now().isoformat()
                        }
                        conversation_history.append(executor_message)
                        await self._broadcast(executor_message)

                # Handle ExecutorCompletedEvent
                elif event_type == 'ExecutorCompletedEvent':
                    executor_id = getattr(event, 'executor_id', 'unknown')
                    print(f"✅ Executor completed: {executor_id}")

                    # REMOVED: campaign_kickoff ExecutorCompletedEvent handler (unreliable - doesn't check final_plan)
                    # Campaign brief is now ONLY sent via CampaignPlannerResponseEvent with final_plan=true

                    # If creative_agent just completed, extract images from workflow state
                    if executor_id == 'creative_agent':
                        print(
                            f"\n🎨 Creative agent completed! Attempting to extract images...")

                        # Check if there's a pending creative HITL - if so, skip this broadcast
                        # because the RequestInfoEvent handler will send the media with the approval flag
                        if pending_requests['is_pending'] and pending_requests.get('request_type') == 'creative_package':
                            print(
                                f"  ⏭️  Skipping media broadcast - creative HITL approval pending")
                        else:
                            # No HITL pending, this is a non-approval creative package
                            try:
                                # Import the workflow state
                                from workflow_v2_with_tools import workflow_state

                                if hasattr(workflow_state, 'creative_package') and workflow_state.creative_package:
                                    package = workflow_state.creative_package
                                    print(
                                        f"✅ Found creative package with {len(package.creatives)} creatives")

                                    # Extract image URLs
                                    media_assets = []
                                    for creative in package.creatives:
                                        # Extract filename from path
                                        import os
                                        filename = os.path.basename(
                                            creative.image_path)

                                        media_asset = {
                                            'type': 'image',
                                            'url': f'http://localhost:8091/images/{filename}',
                                            'caption': creative.caption,
                                            'hashtags': creative.hashtags,
                                            'version': creative.version
                                        }
                                        media_assets.append(media_asset)
                                        print(
                                            f"  - Version {creative.version}: {filename}")

                                    # Send to React UI (pane only, not chat)
                                    media_message = {
                                        'type': 'campaign_data',  # Special type that won't show in chat
                                        'content': f'Generated {len(media_assets)} creative versions',
                                        'timestamp': datetime.now().isoformat(),
                                        'awaiting_input': False,
                                        'campaign_data': {
                                            'media': media_assets
                                        }
                                    }
                                    # Don't add to conversation_history - only broadcast to update the pane
                                    await self._broadcast(media_message)
                                    print(
                                        f"📤 Sent {len(media_assets)} images to React UI (pane only, not chat)")
                                else:
                                    print(
                                        f"⚠️  Creative package not found in workflow_state")
                            except Exception as e:
                                print(f"⚠️  Error extracting images: {e}")
                                import traceback
                                traceback.print_exc()

                # Handle WorkflowOutputEvent - this should contain messages!
                elif event_type == 'WorkflowOutputEvent':
                    print(f"📦 WorkflowOutputEvent received!")
                    print(f"Event attributes: {list(event.__dict__.keys())}")

                    # Try to extract output data
                    if hasattr(event, 'data'):
                        output_data = event.data
                        print(f"Output data type: {type(output_data)}")
                        print(f"Output data: {str(output_data)[:500]}")

                        # Check if it's a Pydantic model
                        if hasattr(output_data, 'model_dump'):
                            try:
                                data_dict = output_data.model_dump()
                                print(
                                    f"Output model keys: {list(data_dict.keys())}")

                                # REMOVED: CampaignPlan detection in WorkflowOutputEvent (unreliable - doesn't check final_plan)
                                # Campaign brief is now ONLY sent via CampaignPlannerResponseEvent with final_plan=true

                                # Check if it's a CreativePackage
                                if 'creatives' in data_dict:
                                    print(
                                        f"🎨 Found CreativePackage in WorkflowOutputEvent!")
                                    media_assets = self._extract_media_assets(
                                        data_dict)
                                    summary = data_dict.get(
                                        'campaign_summary', 'Creative assets generated')

                                    # Check if this creative package is already waiting for HITL approval
                                    # If so, don't broadcast it again (the HITL handler already sent it with needsCreativeApproval)
                                    has_pending_creative_hitl = (
                                        pending_requests['is_pending'] and
                                        pending_requests.get(
                                            'request_type') == 'creative_package'
                                    )

                                    if not has_pending_creative_hitl:
                                        workflow_message = {
                                            'type': 'workflow',
                                            'content': summary,
                                            'timestamp': datetime.now().isoformat(),
                                            'awaiting_input': False,
                                            'campaign_data': {
                                                'media': media_assets
                                            }
                                        }
                                        conversation_history.append(
                                            workflow_message)
                                        await self._broadcast(workflow_message)
                                    else:
                                        print(
                                            f"  ⏭️  Skipping broadcast - creative package already in HITL approval")
                            except Exception as e:
                                print(
                                    f"⚠️  Error processing WorkflowOutputEvent data: {e}")
                                import traceback
                                traceback.print_exc()

            print("✅ Workflow execution complete")

            # Send completion message
            # completion_message = {
            #     'type': 'system',
            #     'content': '✅ Workflow completed! Check the generated_images folder for your marketing images.',
            #     'timestamp': datetime.now().isoformat()
            # }
            # conversation_history.append(completion_message)
            # await self._broadcast(completion_message)

        except Exception as e:
            print(f"❌ Error calling workflow: {e}")
            import traceback
            traceback.print_exc()
            raise

    def _format_campaign_plan(self, plan_data: Dict[str, Any]) -> str:
        """Format CampaignPlan data as markdown for the Campaign Brief pane."""
        lines = []
        lines.append("# 📋 Campaign Plan\n")

        if 'campaign_name' in plan_data:
            lines.append(f"**Campaign:** {plan_data['campaign_name']}\n")

        if 'target_audience' in plan_data:
            lines.append(
                f"**Target Audience:** {plan_data['target_audience']}\n")

        if 'key_message' in plan_data:
            lines.append(f"**Key Message:** {plan_data['key_message']}\n")

        if 'channels' in plan_data and plan_data['channels']:
            lines.append(
                f"\n**Channels:** {', '.join(plan_data['channels'])}\n")

        if 'posting_schedule' in plan_data:
            lines.append(
                f"\n**Posting Schedule:**\n{plan_data['posting_schedule']}\n")

        if 'budget_allocation' in plan_data:
            lines.append(f"\n**Budget:** {plan_data['budget_allocation']}\n")

        return '\n'.join(lines)

    def _extract_media_assets(self, creative_data: Dict[str, Any]) -> list:
        """Extract media assets from CreativePackage data."""
        media_assets = []

        print(
            f"🔍 _extract_media_assets called with data keys: {creative_data.keys()}")
        print(f"🔍 _extract_media_assets data: {creative_data}")

        # Get the creatives list
        creatives = creative_data.get('creatives', [])
        print(f"🔍 Found {len(creatives)} creatives in data")

        for idx, creative in enumerate(creatives):
            print(f"🔍 Processing creative {idx+1}: {creative}")
            print(f"🔍 Creative type: {type(creative)}")

            # Handle both dict and object formats
            if hasattr(creative, 'model_dump'):
                creative_dict = creative.model_dump()
            elif hasattr(creative, '__dict__'):
                creative_dict = vars(creative)
            else:
                creative_dict = creative

            print(
                f"🔍 Creative dict keys: {creative_dict.keys() if isinstance(creative_dict, dict) else 'NOT A DICT'}")

            # Each creative should have an image_path, caption, and hashtags
            image_path = creative_dict.get('image_path', '') if isinstance(
                creative_dict, dict) else ''
            caption = creative_dict.get('caption', '') if isinstance(
                creative_dict, dict) else ''
            hashtags = creative_dict.get('hashtags', []) if isinstance(
                creative_dict, dict) else []
            version = creative_dict.get(
                'version', idx + 1) if isinstance(creative_dict, dict) else idx + 1

            print(
                f"🔍 Extracted - image_path: {image_path[:80] if image_path else 'EMPTY'}")
            print(
                f"🔍 Extracted - caption: {caption[:80] if caption else 'EMPTY'}")
            print(f"🔍 Extracted - version: {version}")

            if image_path:
                # Convert absolute path to relative URL for the React app
                # e.g., /Users/.../generated_images/SmartWatch_Pro_v1.png -> http://localhost:8091/images/SmartWatch_Pro_v1.png
                import os
                filename = os.path.basename(image_path)

                media_asset = {
                    'type': 'image',
                    # Full URL for React app
                    'url': f'http://localhost:8091/images/{filename}',
                    'caption': caption or f'Version {version}',
                    'hashtags': hashtags,
                    'version': version,
                    'path': image_path  # Keep original path for backend reference
                }
                media_assets.append(media_asset)
                print(f"✅ Added media asset {len(media_assets)}: {filename}")
            else:
                print(f"⚠️  Skipping creative {idx+1} - no image_path")

        print(f"🔍 _extract_media_assets returning {len(media_assets)} assets")
        return media_assets

    def _get_channel_icon(self, channel: str) -> str:
        """Get emoji icon for social media channel."""
        channel_lower = channel.lower()
        icons = {
            'instagram': '📷',
            'facebook': '👍',
            'twitter': '🐦',
            'tiktok': '🎵',
            'linkedin': '💼',
            'youtube': '🎥',
            'pinterest': '📌',
        }
        for key, icon in icons.items():
            if key in channel_lower:
                return icon
        return '📱'  # Default icon

    async def serve_image(self, request: web.Request) -> web.Response:
        """Serve generated images from the generated_images folder."""
        filename = request.match_info['filename']

        # Security: only allow alphanumeric, dash, underscore, and dot
        import re
        if not re.match(r'^[a-zA-Z0-9_\-\.]+$', filename):
            return web.Response(status=400, text="Invalid filename")

        # Construct path to generated image
        image_path = Path(__file__).parent / 'generated_images' / filename

        if not image_path.exists():
            return web.Response(status=404, text="Image not found")

        # Serve the image
        return web.FileResponse(image_path)

    # DEPRECATED: session: aiohttp.ClientSession
    async def _process_workflow_run_stream(self, session, entity_id: str, user_input: str):
        """Process workflow using HTTP streaming endpoint."""
        print(f"\n🌊 CALLING WORKFLOW RUN_STREAM VIA HTTP")
        print(f"Entity ID: {entity_id}")
        print(f"Input: {user_input[:200]}...")

        # The workflow streaming endpoint - use GET with input as query parameter
        url = f"{self.workflow_url}/v1/entities/{entity_id}/run_stream"

        print(f"📡 GET {url}")
        print(f"Input parameter: {user_input[:100]}...")

        try:
            async with session.get(
                url,
                params={"input": user_input},
                headers={"Accept": "text/event-stream"}
            ) as resp:
                print(f"📡 Response status: {resp.status}")
                print(f"📡 Response headers: {dict(resp.headers)}")

                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"❌ Workflow returned {resp.status}: {error_text}")
                    raise Exception(
                        f"Workflow returned {resp.status}: {error_text}")

                print(f"✅ Connection established, reading stream...")

                # Read Server-Sent Events
                line_count = 0
                async for line in resp.content:
                    if not line:
                        continue

                    line_text = line.decode('utf-8').rstrip('\n\r')
                    line_count += 1

                    if not line_text or line_text.startswith(':'):
                        continue

                    # Log the raw line
                    print(f"📥 Line {line_count}: {line_text[:200]}")

                    # Try to parse as JSON (newline-delimited JSON format)
                    try:
                        event_data = json.loads(line_text)
                        print(
                            f"✅ Parsed event: {json.dumps(event_data, indent=2)[:400]}")

                        # Extract and broadcast any content
                        await self._handle_workflow_event(entity_id, 'stream', event_data)

                    except json.JSONDecodeError:
                        # Might be SSE format: "data: {...}"
                        if line_text.startswith('data: '):
                            data_json = line_text[6:]
                            try:
                                event_data = json.loads(data_json)
                                print(
                                    f"✅ Parsed SSE data: {json.dumps(event_data, indent=2)[:400]}")
                                await self._handle_workflow_event(entity_id, 'stream', event_data)
                            except json.JSONDecodeError as e:
                                print(f"⚠️  Failed to parse SSE data: {e}")

                print("✅ Stream complete")

            # Send completion message
            # completion_message = {
            #     'type': 'system',
            #     'content': '✅ Workflow completed! Check the generated_images folder for your marketing images.',
            #     'timestamp': datetime.now().isoformat()
            # }
            # conversation_history.append(completion_message)
            # await self._broadcast(completion_message)

        except Exception as e:
            print(f"❌ Error in run_stream: {e}")
            import traceback
            traceback.print_exc()
            raise

    # DEPRECATED: session: aiohttp.ClientSession
    async def _send_response_to_request(self, session, entity_id: str, request_id: str, user_response: str):
        """Send a response to a pending RequestInfoEvent using send_responses_streaming."""
        # The response should be a simple string, just like in the guessing game example
        # The RequestInfoExecutor will pass this string to the handler that expects
        # RequestResponse[StrategyApprovalRequest, str]

        # Simple dict mapping request_id to user's response string
        # The workflow handler will parse "approve" or "reject: feedback"
        response_payload = {
            request_id: user_response
        }

        print(
            f"\n📤 Sending response for request {request_id}: {user_response}")

        # Clear the pending request flag since we're responding
        pending_requests['is_pending'] = False
        pending_requests['request_id'] = None

        # Use send_responses_streaming endpoint
        await self._process_workflow_response_stream(session, entity_id, response_payload)

    # DEPRECATED: session: aiohttp.ClientSession
    async def _process_workflow_response_stream(self, session, entity_id: str, responses: Dict[str, Any]):
        """Process workflow response streaming using send_responses_streaming."""
        # TODO: Implement proper send_responses_streaming endpoint
        # For now, we'll use the responses endpoint with the response data
        payload = {
            "model": entity_id,
            "entity_id": entity_id,
            "responses": responses
        }

        await self._process_workflow_stream(session, entity_id, payload, "/v1/responses")

    # DEPRECATED: session: aiohttp.ClientSession
    async def _process_workflow_stream(self, session, entity_id: str, payload: Dict[str, Any], endpoint: str):
        """Process workflow streaming response."""
        print(f"\n🌊 STARTING STREAM PROCESSING")
        print(f"Endpoint: {self.workflow_url}{endpoint}")
        print(f"Payload: {json.dumps(payload, indent=2)[:300]}")

        async with session.post(
            f"{self.workflow_url}{endpoint}",
            json=payload,
            headers={"Content-Type": "application/json",
                     "Accept": "text/event-stream"}
        ) as resp:
            print(f"📡 Response status: {resp.status}")
            print(f"📡 Response headers: {dict(resp.headers)}")

            if resp.status != 200:
                error_text = await resp.text()
                print(f"❌ Workflow returned {resp.status}: {error_text}")
                raise Exception(
                    f"Workflow returned {resp.status}: {error_text}")

            print(f"✅ Connection established, reading stream...")

            # Read the streaming response as Server-Sent Events
            current_event = None
            current_data = []
            line_count = 0

            async for line in resp.content:
                if not line:
                    continue

                line_text = line.decode('utf-8').rstrip('\n\r')
                line_count += 1

                # Log every line to understand the format
                if line_text:
                    print(f"📥 Line {line_count}: {line_text[:200]}")

                # Try to parse each non-empty line as JSON directly (Agent Framework might send newline-delimited JSON)
                if line_text and not line_text.startswith(':'):
                    try:
                        event_data = json.loads(line_text)
                        print(
                            f"✅ Parsed JSON event: {json.dumps(event_data, indent=2)[:300]}")
                        await self._handle_workflow_event(entity_id, 'data', event_data)
                        continue
                    except json.JSONDecodeError:
                        pass  # Not JSON, might be SSE format

                # SSE format: "event: <type>" or "data: <json>"
                if line_text.startswith('event:'):
                    current_event = line_text[6:].strip()
                    print(f"📌 Event type: {current_event}")
                elif line_text.startswith('data:'):
                    data_content = line_text[5:].strip()
                    if data_content:
                        current_data.append(data_content)
                        print(f"📝 Data fragment: {data_content[:100]}")
                elif line_text == '':
                    # Empty line signals end of event
                    if current_data:
                        full_data = '\n'.join(current_data)
                        try:
                            event_data = json.loads(full_data)
                            print(
                                f"✅ SSE event parsed: {json.dumps(event_data, indent=2)[:300]}")
                            await self._handle_workflow_event(entity_id, current_event or 'data', event_data)
                        except json.JSONDecodeError as e:
                            print(f"⚠️  Failed to parse event data: {e}")
                            print(f"Raw data: {full_data[:500]}")
                        current_data = []
                        current_event = None

            # Handle any remaining data
            if current_data:
                full_data = '\n'.join(current_data)
                try:
                    event_data = json.loads(full_data)
                    await self._handle_workflow_event(entity_id, current_event or 'data', event_data)
                except json.JSONDecodeError:
                    pass

            print(f"\n✅ Workflow completed\n")

    async def _process_agent_framework_event(self, event):
        """Process Agent Framework event objects from run_stream()."""
        from agent_framework import (
            ExecutorInvokedEvent,
            ExecutorCompletedEvent,
            RequestInfoEvent,
            ExecutorFailedEvent,
            WorkflowStatusEvent,
            WorkflowRunState,
            AgentExecutorResponse,
            AgentRunUpdateEvent,
        )

        global pending_requests
        global waiting_for_campaign_info

        # ============================================================================
        # CRITICAL: Campaign Brief Display Logic
        # ============================================================================
        # Campaign briefs are ONLY sent to the campaign brief window when:
        # 1. The response comes from campaign_planner_agent
        # 2. The JSON response has "final_plan": true
        #
        # Intermediate messages (final_plan: false) are follow-up questions
        # that should appear in the chat, NOT in the campaign brief window.
        #
        # There are THREE event handlers that implement this check:
        # - CampaignPlannerResponseEvent (custom event from workflow)
        # - AgentRunUpdateEvent (standard event with campaign_planner_agent)
        # - AgentExecutorResponse (standard event with campaign_planner_agent)
        #
        # DO NOT add campaign brief logic elsewhere without checking final_plan!
        # ============================================================================

        # Check for custom CampaignPlannerResponseEvent by class name
        if type(event).__name__ == 'CampaignPlannerResponseEvent':
            print(f"\n💬 ===== CAMPAIGN PLANNER RESPONSE EVENT =====")
            print(f"💬 Full Response Text:")
            response_text = event.response_text
            print(response_text)
            print(f"💬 ===========================================\n")

            # Parse JSON response
            try:
                import json
                import re

                # Strip markdown code fences if present
                cleaned_text = response_text.strip()
                if cleaned_text.startswith('```'):
                    # Remove opening fence (e.g., ```json)
                    cleaned_text = re.sub(r'^```[a-z]*\n', '', cleaned_text)
                    # Remove closing fence
                    cleaned_text = re.sub(r'\n```$', '', cleaned_text)
                    cleaned_text = cleaned_text.strip()

                print(
                    f"🔧 DEBUG: Attempting to parse JSON (length: {len(cleaned_text)})")
                print(f"🔧 DEBUG: First 500 chars: {cleaned_text[:500]}")

                response_data = json.loads(cleaned_text)
                agent_response = response_data.get('agent_response', '')
                final_plan = response_data.get('final_plan', False)
                campaign_title = response_data.get('campaign_title', '')

                print(f"   📋 Campaign Planner JSON Parsed:")
                print(f"      final_plan: {final_plan}")
                print(f"      campaign_title: {campaign_title}")
                print(f"      response: {agent_response[:200]}...")

                if final_plan:
                    # This is the final campaign brief - send to campaign brief box
                    waiting_for_campaign_info = False  # Reset flag
                    await self._broadcast({
                        'type': 'campaign_data',
                        'content': agent_response,
                        'timestamp': datetime.now().isoformat(),
                        'campaign_data': {
                            'brief': agent_response,
                            'isFormattedBrief': True,
                            'campaignName': campaign_title if campaign_title else None
                        }
                    })
                else:
                    # This is a follow-up question - send to chat
                    waiting_for_campaign_info = True  # Set flag - workflow is waiting for user
                    await self._broadcast({
                        'type': 'assistant',
                        'content': agent_response,
                        'timestamp': datetime.now().isoformat(),
                        'awaiting_input': True
                    })
            except json.JSONDecodeError as e:
                # Fallback if not valid JSON - display as regular message
                print(
                    f"   ⚠️ Campaign planner response is not valid JSON: {e}")
                print(f"   ⚠️ Raw response text (first 1000 chars):")
                print(f"   {repr(response_text[:1000])}")
                print(f"   ⚠️ Displaying as text instead")
                await self._broadcast({
                    'type': 'assistant',
                    'content': response_text,
                    'timestamp': datetime.now().isoformat(),
                    'awaiting_input': True
                })
            return  # Done processing this event

        # Check for custom CreativeAssetsGeneratedEvent by class name
        if type(event).__name__ == 'CreativeAssetsGeneratedEvent':
            print(f"\n🎨 ===== CREATIVE ASSETS GENERATED EVENT =====")
            print(f"🎨 Number of assets: {len(event.assets)}")

            # Store assets in instance variable for later use
            if not hasattr(self, '_media_assets'):
                self._media_assets = []

            # Convert file:// URLs to data URIs for browser display
            converted_assets = []
            for asset in event.assets:
                asset_copy = asset.copy()
                if 'url' in asset_copy and asset_copy['url'].startswith('file://'):
                    # Convert file path to data URI
                    asset_copy['url'] = convert_file_to_data_uri(
                        asset_copy['url'])
                converted_assets.append(asset_copy)

            self._media_assets = converted_assets  # Replace with new assets

            for idx, asset in enumerate(converted_assets):
                url_preview = asset.get('url', '')[
                    :50] + '...' if len(asset.get('url', '')) > 50 else asset.get('url', '')
                print(
                    f"🎨 Asset {idx + 1}: {asset.get('type')} - {asset.get('filename')} - {url_preview}")

            print(f"🎨 Total media assets stored: {len(self._media_assets)}")
            print(f"🎨 ==========================================\n")
            return  # Done processing this event

        # Check for custom MarketSelectionQuestionEvent by class name
        if type(event).__name__ == 'MarketSelectionQuestionEvent':
            print(f"\n🌍 ===== MARKET SELECTION QUESTION EVENT =====")
            question_text = event.question_text
            print(f"🌍 Question: {question_text}")

            # Send as a message styled as coming from the localization agent
            await self._broadcast({
                'type': 'workflow',
                'content': question_text,
                'timestamp': datetime.now().isoformat(),
                'sender': 'workflow',
                'agent_name': 'Localization Agent'
            })

            # Clear the creative approval state now that user has approved
            clear_approval_message = {
                'type': 'campaign_data',
                'timestamp': datetime.now().isoformat(),
                'campaign_data': {
                    'needsCreativeApproval': False
                }
            }
            conversation_history.append(clear_approval_message)
            await self._broadcast(clear_approval_message)

            print(f"🌍 Sent market selection question to chat")
            print(f"🌍 Cleared creative approval state")
            print(f"🌍 =============================================\n")
            return  # Done processing this event

        # Check for custom LocalizationResponseEvent by class name
        if type(event).__name__ == 'LocalizationResponseEvent':
            print(f"\n🌍 ===== LOCALIZATION RESPONSE EVENT =====")
            print(f"🌍 Full Response Text:")
            response_text = event.response_text
            print(response_text)
            print(f"🌍 ========================================\n")

            # Parse JSON array of translations
            try:
                import json
                import re

                # Strip markdown code fences if present
                cleaned_text = response_text.strip()
                if cleaned_text.startswith('```'):
                    cleaned_text = re.sub(r'^```[a-z]*\n', '', cleaned_text)
                    cleaned_text = re.sub(r'\n```$', '', cleaned_text)
                    cleaned_text = cleaned_text.strip()

                translations = json.loads(cleaned_text)

                print(f"   📋 Localization JSON Parsed:")
                print(f"      translations count: {len(translations)}")
                print(
                    f"   🔍 DEBUG: hasattr(self, '_media_assets'): {hasattr(self, '_media_assets')}")
                if hasattr(self, '_media_assets'):
                    print(
                        f"   🔍 DEBUG: len(self._media_assets): {len(self._media_assets)}")
                    for idx, asset in enumerate(self._media_assets):
                        print(
                            f"   🔍   Asset {idx}: {asset.get('type')} - {asset.get('url')[:50]}...")
                else:
                    print(f"   ⚠️ ERROR: self._media_assets does not exist!")

                # Combine translations with stored media assets
                localizations = []
                for idx, translation in enumerate(translations):
                    # Get corresponding media asset (should be in same order)
                    if hasattr(self, '_media_assets') and idx < len(self._media_assets):
                        asset = self._media_assets[idx]

                        # Extract market and language from translation
                        market = translation.get('market', 'Unknown')
                        language_code = translation.get('language', 'es-ES')

                        # Map language codes to friendly names
                        language_map = {
                            'es-ES': 'Spanish (Spain)',
                            'es-MX': 'Spanish (Mexico)',
                            'es-LA': 'Spanish (Latin America)',
                            'fr-FR': 'French',
                            'de-DE': 'German',
                            'pt-BR': 'Portuguese (Brazil)',
                            'es': 'Spanish'
                        }
                        language_name = language_map.get(
                            language_code, language_code)

                        # Extract just the language code for locale (e.g., 'es' from 'es-ES')
                        locale = language_code.split(
                            '-')[0] if '-' in language_code else language_code

                        localization = {
                            'type': asset.get('type'),
                            # Frontend expects 'image' not 'url'
                            'image': asset.get('url'),
                            'caption': translation.get('translation', ''),
                            'hashtags': '',  # Hashtags are included in caption now
                            'language': language_name,
                            'locale': locale,
                            'market': market
                        }
                        localizations.append(localization)

                print(
                    f"   ✅ Created {len(localizations)} localized assets with images")

                # Send to localization section (same format as media assets)
                await self._broadcast({
                    'type': 'campaign_data',
                    'content': f'Localized {len(localizations)} items',
                    'timestamp': datetime.now().isoformat(),
                    'campaign_data': {
                        'localizations': localizations
                    }
                })
            except json.JSONDecodeError as e:
                # Fallback if not valid JSON - display as text
                print(f"   ⚠️ Localization response is not valid JSON: {e}")
                print(
                    f"   ⚠️ Raw response (first 500 chars): {repr(cleaned_text[:500])}")
                print(f"   ⚠️ Displaying as text instead")
                await self._broadcast({
                    'type': 'assistant',
                    'content': response_text,
                    'timestamp': datetime.now().isoformat()
                })
            return  # Done processing this event

        # Check for custom PublishingScheduleResponseEvent by class name
        if type(event).__name__ == 'PublishingScheduleResponseEvent':
            print(f"\n📅 ===== PUBLISHING SCHEDULE RESPONSE EVENT =====")
            print(f"📅 Full Response Text:")
            response_text = event.response_text
            print(response_text)
            print(f"📅 ===============================================\n")

            # Clear media assets from creative stage - we're now in publishing phase
            if hasattr(self, '_media_assets'):
                print(
                    f"   🧹 Clearing {len(self._media_assets)} media assets (moving to publishing phase)")
                self._media_assets = []

            # Parse JSON array of schedule items
            try:
                import json
                import re

                # Strip markdown code fences if present
                cleaned_text = response_text.strip()
                if cleaned_text.startswith('```'):
                    cleaned_text = re.sub(r'^```[a-z]*\n', '', cleaned_text)
                    cleaned_text = re.sub(r'\n```$', '', cleaned_text)
                    cleaned_text = cleaned_text.strip()

                schedule_items = json.loads(cleaned_text)

                print(f"   📋 Publishing Schedule JSON Parsed:")
                print(f"      schedule items count: {len(schedule_items)}")

                # Send to schedule section
                await self._broadcast({
                    'type': 'campaign_data',
                    'content': f'Generated publishing schedule with {len(schedule_items)} items',
                    'timestamp': datetime.now().isoformat(),
                    'campaign_data': {
                        'schedule': schedule_items
                    }
                })
            except json.JSONDecodeError as e:
                # Fallback if not valid JSON - display as text
                print(f"   ⚠️ Schedule response is not valid JSON: {e}")
                print(
                    f"   ⚠️ Raw response (first 500 chars): {repr(cleaned_text[:500])}")
                print(f"   ⚠️ Displaying as text instead")
                await self._broadcast({
                    'type': 'assistant',
                    'content': response_text,
                    'timestamp': datetime.now().isoformat()
                })
            return  # Done processing this event

        # Get event type name once for all checks
        event_type_name = type(event).__name__

        # Skip printing for noisy events (but still process them)
        if event_type_name != 'AgentRunUpdateEvent':
            print(f"\n🔍 Event Type: {event_type_name}")
        # else:
            # Temporarily log AgentRunUpdateEvent to debug tool results
            # print(f"\n🔧 AgentRunUpdateEvent received")

        # Check for tool results in AgentRunUpdateEvent
        if event_type_name == 'AgentRunUpdateEvent':
            # Extract tool call results if present - the data is in event.data, not event.agent_run
            if hasattr(event, 'data'):
                # Check if this is from creative_agent (where we expect tool results)
                # Disabled verbose logging - uncomment if needed for debugging
                # if event.executor_id == 'creative_agent':
                #     print(f"🔧 DEBUG: AgentRunResponseUpdate from creative_agent")
                #     print(f"🔧   - Has contents: {hasattr(event.data, 'contents')}")
                #
                #     if hasattr(event.data, 'contents') and event.data.contents:
                #         print(f"🔧   - Number of content items: {len(event.data.contents)}")
                #         for idx, content_item in enumerate(event.data.contents):
                #             print(f"🔧   - Content {idx} type: {type(content_item).__name__}")
                #             print(f"🔧   - Content {idx} attributes: {dir(content_item)}")
                #             print(f"🔧   - Content {idx} __dict__: {content_item.__dict__ if hasattr(content_item, '__dict__') else 'No __dict__'}")
                #
                #     # Also check raw_representation
                #     if hasattr(event.data, 'raw_representation'):
                #         print(f"🔧   - Has raw_representation: True")
                #         raw = event.data.raw_representation
                #         print(f"🔧   - raw_representation type: {type(raw).__name__}")
                #         print(f"🔧   - raw_representation attributes: {dir(raw)}")
                #         if hasattr(raw, '__dict__'):
                #             print(f"🔧   - raw_representation __dict__: {raw.__dict__}")

                if hasattr(event.data, 'messages'):
                    # Disabled verbose logging - uncomment if needed for debugging
                    # print(f"🔧 DEBUG: Found AgentRunResponseUpdate with messages")
                    # print(f"🔧   - Number of messages: {len(event.data.messages)}")
                    for idx, msg in enumerate(event.data.messages):
                        # print(f"🔧   - Message {idx} attributes: {dir(msg)}")
                        if hasattr(msg, 'content') and isinstance(msg.content, list):
                            # print(f"🔧     - Content items: {len(msg.content)}")
                            for cidx, content_item in enumerate(msg.content):
                                # print(f"🔧     - Content item {cidx} type: {type(content_item).__name__}")
                                # print(f"🔧     - Content item {cidx} attributes: {dir(content_item)}")
                                if hasattr(content_item, 'output'):
                                    # This is a tool result
                                    try:
                                        import json
                                        tool_result = json.loads(
                                            content_item.output)
                                        # print(f"🔧 ✅ Found tool result with type: {tool_result.get('type', 'UNKNOWN')}")
                                        if tool_result.get('type') in ['image', 'video']:
                                            # Store tool result for later processing
                                            if not hasattr(self, '_media_assets'):
                                                self._media_assets = []
                                                # print(f"🔧 DEBUG: Initialized _media_assets list")
                                            self._media_assets.append(
                                                tool_result)
                                            print(
                                                f"📸 Captured {tool_result['type']}: {tool_result.get('filename', 'unknown')}")
                                            # print(f"📸 Total media assets stored: {len(self._media_assets)}")
                                    except (json.JSONDecodeError, AttributeError) as e:
                                        print(
                                            f"🔧 DEBUG: Error parsing tool result: {e}")
                # else:
                    # print(f"🔧 DEBUG: AgentRunResponseUpdate has no messages attribute")
            # else:
                # print(f"🔧 DEBUG: AgentRunUpdateEvent has no data attribute")

        # DEBUG: Print event details for WorkflowStatusEvent
        if isinstance(event, WorkflowStatusEvent):
            # Disabled verbose logging - uncomment if needed
            # print(f"🔍 DEBUG WorkflowStatusEvent state: {event.state}")
            # if hasattr(event, 'pending_requests'):
            #     print(f"🔍 DEBUG pending_requests in event: {event.pending_requests}")
            pass

        # DEBUG: Check ExecutorCompletedEvent for creative_agent (DISABLED - too verbose)
        # if event_type_name == 'ExecutorCompletedEvent' and event.executor_id == 'creative_agent':
        #     print(f"\n🎨 ===== CREATIVE AGENT COMPLETED =====")
        #     print(f"🎨 Event attributes: {dir(event)}")
        #     if hasattr(event, 'data'):
        #         print(f"🎨 Event.data type: {type(event.data).__name__}")
        #         print(f"🎨 Event.data attributes: {dir(event.data)}")
        #         if hasattr(event.data, '__dict__'):
        #             print(f"🎨 Event.data __dict__: {event.data.__dict__}")
        #     print(f"🎨 ======================================\n")

        # if isinstance(event, ExecutorInvokedEvent):
        #     # Executor started - show "Running: X" message (skip internal routing executors)
        #     executor_id = event.executor_id
        #     if executor_id not in ['coordinator', 'reviewer']:
        #         executor_name = executor_id.replace('_', ' ').title()
        #         await self._broadcast({
        #             'type': 'system',
        #             'content': f"Running: {executor_name}...",
        #             'timestamp': datetime.now().isoformat()
        #         })

        elif isinstance(event, AgentExecutorResponse):
            # Agent has produced output - display it in the chat
            executor_name = event.executor_id.replace('_', ' ').title()
            agent_text = event.agent_run_response.text if hasattr(
                event.agent_run_response, 'text') else str(event.agent_run_response)

            print(f"\n💬 ===== AGENT RESPONSE =====")
            print(f"💬 Agent: {executor_name} (id: {event.executor_id})")
            print(f"💬 Full Response Text:")
            print(agent_text)
            print(f"💬 ==========================\n")

            # Special handling for campaign_planner_agent JSON response
            if event.executor_id == 'campaign_planner_agent':
                try:
                    import json
                    response_data = json.loads(agent_text)
                    agent_response = response_data.get('agent_response', '')
                    final_plan = response_data.get('final_plan', False)
                    campaign_title = response_data.get('campaign_title', '')

                    print(f"   📋 Campaign Planner JSON Parsed:")
                    print(f"      final_plan: {final_plan}")
                    print(f"      campaign_title: {campaign_title}")
                    print(f"      response: {agent_response[:200]}...")

                    if final_plan:
                        # This is the final campaign brief - send to campaign brief box
                        await self._broadcast({
                            'type': 'campaign_data',
                            'content': agent_response,
                            'timestamp': datetime.now().isoformat(),
                            'campaign_data': {
                                'brief': agent_response,
                                'isFormattedBrief': True,
                                'campaignName': campaign_title if campaign_title else None
                            }
                        })
                    else:
                        # This is a follow-up question - send to chat
                        await self._broadcast({
                            'type': 'assistant',
                            'content': agent_response,
                            'timestamp': datetime.now().isoformat(),
                            'awaiting_input': True
                        })
                except json.JSONDecodeError as e:
                    # Fallback if not valid JSON - display as regular message
                    print(
                        f"   ⚠️ Campaign planner response is not valid JSON: {e}")
                    print(f"   ⚠️ Displaying as text instead")
                    await self._broadcast({
                        'type': 'assistant',
                        'content': agent_text,
                        'timestamp': datetime.now().isoformat(),
                        'awaiting_input': True
                    })
            else:
                # Other agents - broadcast to chat window
                await self._broadcast({
                    'type': 'assistant',
                    'content': f"**{executor_name}:**\n\n{agent_text}",
                    'timestamp': datetime.now().isoformat()
                })

        elif isinstance(event, RequestInfoEvent):
            # HITL request - store and broadcast with approval UI
            pending_requests['is_pending'] = True
            pending_requests['request_id'] = event.request_id
            pending_requests['request_data'] = event.data

            # Disabled verbose debug logging
            # print(f"🔍 DEBUG RequestInfoEvent - event.data type: {type(event.data)}")
            # if hasattr(event.data, '__dict__'):
            #     print(f"🔍 DEBUG RequestInfoEvent - event.data.__dict__ keys: {event.data.__dict__.keys()}")

            # Check if this is a DraftFeedbackRequest (the generic HITL format)
            if hasattr(event.data, 'draft_text') and hasattr(event.data, 'prompt'):
                # print(f"🔍 DEBUG DraftFeedbackRequest detected")
                # print(f"   Prompt: {event.data.prompt[:100]}...")
                # print(f"   Draft text preview: {event.data.draft_text[:200]}...")

                # Extract and store media_assets if present
                if hasattr(event.data, 'media_assets') and event.data.media_assets:
                    # Convert file:// URLs to data URIs before storing
                    converted_assets = []
                    for asset in event.data.media_assets:
                        asset_copy = asset.copy()
                        if 'url' in asset_copy and asset_copy['url'].startswith('file://'):
                            asset_copy['url'] = convert_file_to_data_uri(
                                asset_copy['url'])
                        converted_assets.append(asset_copy)

                    self._media_assets = converted_assets
                    print(
                        f"🎨 Stored {len(self._media_assets)} media assets from DraftFeedbackRequest")
                    for idx, asset in enumerate(self._media_assets):
                        print(
                            f"   Asset {idx+1}: {asset.get('type')} - {asset.get('filename')}")

                # Try to parse draft_text as JSON to see if it contains creative assets
                # try:
                #     import json
                #     draft_data = json.loads(event.data.draft_text)
                #     print(f"🔍 DEBUG Draft text is JSON with keys: {draft_data.keys()}")
                # except:
                #     print(f"🔍 DEBUG Draft text is not JSON, it's plain text")
                pass

            # Check if this is a campaign plan review, creative review, or publishing review
            if hasattr(event.data, 'campaign_plan') and event.data.campaign_plan:
                pending_requests['request_type'] = 'campaign_plan'
                # Campaign plan review
                campaign_plan_obj = event.data.campaign_plan

                # Convert CampaignPlan object to formatted markdown string
                if campaign_plan_obj:
                    plan_dict = campaign_plan_obj.model_dump() if hasattr(
                        campaign_plan_obj, 'model_dump') else vars(campaign_plan_obj)
                    formatted_plan = self._format_campaign_plan(plan_dict)
                else:
                    formatted_plan = "Campaign plan not available"

                # Send approval state to campaign details pane (not chat)
                await self._broadcast({
                    'type': 'approval_required',
                    'request_id': event.request_id,
                    'campaign_plan': formatted_plan
                })
                print(
                    f"📋 Stored campaign plan HITL request: {event.request_id}")

            elif hasattr(event.data, 'creative_package') and event.data.creative_package:
                pending_requests['request_type'] = 'creative_package'
                # Creative assets review
                creative_package = event.data.creative_package

                # Extract media assets from the creative package
                if hasattr(creative_package, 'model_dump'):
                    data_dict = creative_package.model_dump()
                else:
                    data_dict = vars(creative_package)

                print(
                    f"🔍 DEBUG: creative_package data_dict keys: {data_dict.keys()}")
                print(f"🔍 DEBUG: creative_package full data: {data_dict}")

                media_assets = self._extract_media_assets(data_dict)

                print(f"🔍 DEBUG: Extracted {len(media_assets)} media assets:")
                for idx, asset in enumerate(media_assets):
                    print(
                        f"   {idx+1}. Type: {asset.get('type')}, URL: {asset.get('url', 'NO URL')[:80]}")
                    print(
                        f"      Caption: {asset.get('caption', 'NO CAPTION')[:80]}...")

                # DIAGNOSTIC: If no media extracted, check if creatives exist
                if len(media_assets) == 0:
                    print(f"❌ WARNING: No media assets extracted!")
                    print(
                        f"   'creatives' in data_dict: {'creatives' in data_dict}")
                    if 'creatives' in data_dict:
                        print(
                            f"   Length of creatives: {len(data_dict['creatives'])}")
                        print(
                            f"   First creative: {data_dict['creatives'][0] if data_dict['creatives'] else 'None'}")

                # Extract the prompt text from the request
                prompt_text = getattr(
                    event.data, 'prompt', '🎨 **CREATIVE ASSETS READY FOR REVIEW**')

                # Send creative approval required message WITH media data AND prompt
                # This will display in the media pane with border and approval buttons
                broadcast_msg = {
                    'type': 'creative_approval_required',
                    'request_id': event.request_id,
                    'media': media_assets,
                    'prompt': prompt_text,  # Include prompt for display in media section
                }

                print(f"\n🎨 ========== CREATIVE APPROVAL BROADCAST ==========")
                print(f"Type: {broadcast_msg['type']}")
                print(f"Request ID: {broadcast_msg['request_id']}")
                print(f"Media count: {len(broadcast_msg['media'])}")
                print(f"Prompt: {broadcast_msg['prompt'][:100]}...")
                if broadcast_msg['media']:
                    print(f"First media item: {broadcast_msg['media'][0]}")
                print(f"================================================\n")

                await self._broadcast(broadcast_msg)
                print(
                    f"🎨 Stored creative assets HITL request: {event.request_id} with {len(media_assets)} media items")

            elif hasattr(event.data, 'localization_package') and event.data.localization_package:
                pending_requests['request_type'] = 'localization_package'
                # Localization review
                localization_package = event.data.localization_package

                # Extract localized versions
                if hasattr(localization_package, 'model_dump'):
                    data_dict = localization_package.model_dump()
                else:
                    data_dict = vars(localization_package)

                localized_items = []
                for item in data_dict.get('localized_versions', []):
                    localized_item = {
                        'locale': item.get('locale', ''),
                        'language': item.get('language', ''),
                        'market': item.get('market_name', ''),
                        'caption': item.get('caption', ''),
                        'hashtags': item.get('hashtags', []),
                        'cultural_notes': item.get('cultural_adaptations', ''),
                        'image': item.get('image_path', ''),
                    }
                    localized_items.append(localized_item)

                # Send localization approval required message in campaign_data format
                await self._broadcast({
                    'type': 'campaign_data',
                    'request_id': event.request_id,
                    'campaign_data': {
                        'localizations': localized_items,
                        'needsLocalizationApproval': True,
                    }
                })
                print(
                    f"🌍 Stored localization HITL request: {event.request_id} with {len(localized_items)} localized versions")

            elif hasattr(event.data, 'publishing_plan') and event.data.publishing_plan:
                pending_requests['request_type'] = 'publishing_plan'
                # Publishing schedule review
                publishing_plan = event.data.publishing_plan

                # Extract schedule items
                if hasattr(publishing_plan, 'model_dump'):
                    data_dict = publishing_plan.model_dump()
                else:
                    data_dict = vars(publishing_plan)

                schedule_items = []
                for item in data_dict.get('schedule', []):
                    schedule_item = {
                        'channel': item.get('channel', ''),
                        'datetime': item.get('post_date', ''),
                        'creative_version': item.get('creative_version', 1),
                        'caption': item.get('caption', ''),
                        'hashtags': item.get('hashtags', []),
                        'target_notes': item.get('target_audience_notes', ''),
                        'icon': self._get_channel_icon(item.get('channel', '')),
                        'status': 'scheduled'
                    }
                    schedule_items.append(schedule_item)

                # Send publishing approval required message WITH schedule data included
                await self._broadcast({
                    'type': 'publishing_approval_required',
                    'request_id': event.request_id,
                    'schedule': schedule_items,
                })
                print(
                    f"📅 Stored publishing schedule HITL request: {event.request_id} with {len(schedule_items)} posts")
            else:
                # Handle generic DraftFeedbackRequest from marketing-workflow.py
                pending_requests['request_type'] = 'draft_feedback'

                # Extract the draft text and prompt
                draft_text = getattr(event.data, 'draft_text', '')
                prompt_text = getattr(
                    event.data, 'prompt', 'Please review and provide feedback.')

                print(f"📝 Draft feedback request: {event.request_id}")
                print(f"   Draft preview: {draft_text[:200]}...")

                # Store original draft_text before any modifications
                original_draft_text = draft_text

                # Get media assets if we captured any from tool results
                media_assets = []
                caption_text = ""
                if hasattr(self, '_media_assets') and self._media_assets:
                    media_assets = self._media_assets.copy()
                    print(
                        f"📸 Including {len(media_assets)} media assets with creative")

                    # Build a text summary of captions for the localization agent
                    captions_for_loc = []
                    for i, asset in enumerate(media_assets, 1):
                        asset_type = asset.get('type', 'media')
                        caption = asset.get('caption', '')
                        hashtags = asset.get('hashtags', '')
                        if caption:
                            captions_for_loc.append(
                                f"{asset_type.title()} {i} Caption: {caption}")
                        if hashtags:
                            captions_for_loc.append(
                                f"{asset_type.title()} {i} Hashtags: {hashtags}")

                    if captions_for_loc:
                        caption_text = "\n\n".join(captions_for_loc)
                        draft_text = caption_text  # Replace draft_text with caption text for localization
                        print(
                            f"📝 Built caption text for localization:\n{caption_text}")

                    # Don't clear yet - we'll clear after sending to avoid losing them

                # NOTE: Market selection question is now handled by MarketSelectionQuestionEvent
                # and sent separately, so we don't need to send it here

                # Send creative assets to Social Media Assets box with approval buttons
                # OR send schedule to Publish Schedule box
                if media_assets:
                    # This is creative approval (has media assets)
                    await self._broadcast({
                        'type': 'campaign_data',
                        'content': draft_text,
                        'timestamp': datetime.now().isoformat(),
                        'request_id': event.request_id,
                        'campaign_data': {
                            'creativeText': draft_text,
                            'media': media_assets,
                            'needsCreativeApproval': True,
                            'prompt': prompt_text
                        }
                    })
                else:
                    # This is schedule approval (no media assets)
                    await self._broadcast({
                        'type': 'campaign_data',
                        'content': draft_text,
                        'timestamp': datetime.now().isoformat(),
                        'request_id': event.request_id,
                        'campaign_data': {
                            'needsPublishingApproval': True,
                            'prompt': prompt_text
                        }
                    })

                # Don't clear media assets yet - we need them for localization
                # if hasattr(self, '_media_assets'):
                #     self._media_assets = []

        elif isinstance(event, ExecutorCompletedEvent):
            # Executor finished
            executor_id = event.executor_id
            print(f"✅ Executor completed: {executor_id}")

            # Debug: Check what attributes are available
            if hasattr(event, '__dict__'):
                attrs = {k: v for k, v in event.__dict__.items()
                         if not k.startswith('_')}
                print(f"   Available attributes: {list(attrs.keys())}")

            # Check if this executor has response data we can display
            if hasattr(event, 'result') and event.result:
                print(f"   Result type: {type(event.result).__name__}")
                if hasattr(event.result, 'text'):
                    result_text = event.result.text
                    print(f"   Result text: {result_text[:200]}...")

                    # Special handling for campaign_planner_agent JSON response
                    if executor_id == 'campaign_planner_agent':
                        try:
                            import json
                            response_data = json.loads(result_text)
                            agent_response = response_data.get(
                                'agent_response', '')
                            final_plan = response_data.get('final_plan', False)
                            campaign_title = response_data.get(
                                'campaign_title', '')

                            print(f"   📋 Campaign Planner Response:")
                            print(f"      final_plan: {final_plan}")
                            print(f"      campaign_title: {campaign_title}")
                            print(f"      response: {agent_response[:200]}...")

                            if final_plan:
                                # This is the final campaign brief - send to campaign brief box
                                await self._broadcast({
                                    'type': 'campaign_data',
                                    'content': agent_response,
                                    'timestamp': datetime.now().isoformat(),
                                    'campaign_data': {
                                        'brief': agent_response,
                                        'isFormattedBrief': True,
                                        'campaignName': campaign_title if campaign_title else None
                                    }
                                })
                            else:
                                # This is a follow-up question - send to chat
                                await self._broadcast({
                                    'type': 'assistant',
                                    'content': agent_response,
                                    'timestamp': datetime.now().isoformat(),
                                    'awaiting_input': True
                                })
                        except json.JSONDecodeError:
                            # Fallback if not valid JSON
                            print(
                                f"   ⚠️ Campaign planner response is not valid JSON, displaying as text")
                            await self._broadcast({
                                'type': 'assistant',
                                'content': result_text,
                                'timestamp': datetime.now().isoformat()
                            })

                    # Display other agent outputs in chat (skip coordinator and reviewer)
                    elif executor_id not in ['coordinator', 'reviewer', 'hitl_review']:
                        executor_name = executor_id.replace('_', ' ').title()
                        await self._broadcast({
                            'type': 'assistant',
                            'content': f"**{executor_name}:**\n\n{result_text}",
                            'timestamp': datetime.now().isoformat()
                        })

            # Note: Creative assets are only broadcast when RequestInfoEvent (HITL) is received
            # This ensures images don't appear until after critique agent approval

        elif isinstance(event, ExecutorFailedEvent):
            # Error occurred
            await self._broadcast({
                'type': 'system',
                'content': f"❌ Error in {event.executor_id}: {event.details}"
            })

        elif isinstance(event, WorkflowStatusEvent):
            # Check if workflow is waiting for input
            if event.state == WorkflowRunState.IDLE_WITH_PENDING_REQUESTS:
                print(f"⏸️  Workflow paused - waiting for human input")
                # Don't send completion message - workflow is paused
            elif event.state == WorkflowRunState.IDLE:
                # Workflow reached IDLE state - check if it's because of completion or pause
                if waiting_for_campaign_info:
                    # Waiting for user to provide more campaign info
                    print(f"⏸️  Workflow paused - waiting for campaign planner info")
                elif not pending_requests['is_pending']:
                    # No pending requests, workflow is truly complete
                    # Add 3 second pause before showing completion message
                    await asyncio.sleep(3)
                    await self._broadcast({
                        'type': 'system',
                        'content': '✅ Workflow completed! Check the generated_images folder for your marketing images.'
                    })
                    print(f"\n✅ Workflow completed\n")

        else:
            # Log any unhandled event types to help with debugging
            event_type_name = type(event).__name__
            if event_type_name not in ['AgentRunUpdateEvent']:
                print(f"⚠️  Unhandled event type: {event_type_name}")
                if hasattr(event, '__dict__'):
                    print(
                        f"    Event attributes: {list(event.__dict__.keys())}")

    async def _handle_workflow_event(self, entity_id: str, event_type: str, event_data: Dict[str, Any]):
        """Handle individual workflow events."""
        print(f"\n🔍 EVENT TYPE: {event_type}")
        print(f"📦 Full event data: {json.dumps(event_data, indent=2)[:500]}")

        # Check what kind of event this is based on content
        event_object = event_data.get('object', '')

        # Handle response.output_item.done events (these contain the actual messages)
        if event_object == 'response.output_item.done' or event_type == 'response.output_item.done':
            print("✨ Found output_item.done event")
            item = event_data.get('item', {})
            content_items = item.get('content', [])

            for content_item in content_items:
                if content_item.get('type') == 'output_text':
                    text = content_item.get('text', '')
                    if text and text.strip():
                        print(f"📝 Broadcasting text: {text[:100]}...")
                        workflow_message = {
                            'type': 'assistant',
                            'content': text,
                            'timestamp': datetime.now().isoformat(),
                            'awaiting_input': False
                        }
                        conversation_history.append(workflow_message)
                        await self._broadcast(workflow_message)

        # Handle response.output_item.delta events (streaming text)
        elif event_object == 'response.output_item.delta' or event_type == 'response.output_item.delta':
            print("📨 Found output_item.delta event")
            delta = event_data.get('delta', {})
            content_items = delta.get('content', [])

            for content_item in content_items:
                if content_item.get('type') == 'output_text':
                    text = content_item.get('text', '')
                    if text:
                        print(f"📝 Streaming text delta: {text[:100]}...")
                        workflow_message = {
                            'type': 'assistant',
                            'content': text,
                            'timestamp': datetime.now().isoformat(),
                            'awaiting_input': False
                        }
                        conversation_history.append(workflow_message)
                        await self._broadcast(workflow_message)

        # Handle message events from ctx.send_message()
        elif event_type == 'message' or event_object == 'message':
            print("💬 Found message event")
            role = event_data.get('role', 'assistant')
            content = event_data.get('content', '')

            if content:
                workflow_message = {
                    'type': 'assistant' if role == 'assistant' else 'workflow',
                    'content': content,
                    'timestamp': datetime.now().isoformat(),
                    'awaiting_input': False
                }
                conversation_history.append(workflow_message)
                await self._broadcast(workflow_message)

        elif event_type == 'request_info':
            # Human-in-the-loop request
            request_id = event_data.get('request_id')
            request_data = event_data.get('request', {})
            prompt = request_data.get('prompt', '')

            print(f"\n⏸️  HITL Request ID: {request_id}")

            # Store pending request
            pending_requests['request_id'] = request_id
            pending_requests['entity_id'] = entity_id
            pending_requests['is_pending'] = True
            pending_requests['request_data'] = request_data

            # Broadcast approval request to frontend
            workflow_message = {
                'type': 'assistant',
                'content': f"[APPROVAL_REQUIRED]\n{prompt}",
                'timestamp': datetime.now().isoformat(),
                'awaiting_input': True,
                'request_id': request_id
            }
            conversation_history.append(workflow_message)
            await self._broadcast(workflow_message)

        elif event_type == 'tool_call' or event_data.get('type') == 'tool_call':
            # Tool execution notification
            tool_name = event_data.get('name', 'unknown')
            tool_args = event_data.get('arguments', {})

            message_text = f"🔧 Calling tool: {tool_name}"
            if 'image_prompt' in tool_args:
                message_text += f"\n📸 Generating image: {tool_args['image_prompt'][:100]}..."

            workflow_message = {
                'type': 'system',
                'content': message_text,
                'timestamp': datetime.now().isoformat()
            }
            conversation_history.append(workflow_message)
            await self._broadcast(workflow_message)

        # Check for response completion
        if event_data.get('object') == 'response':
            # Extract any final output
            if 'output' in event_data:
                for output_item in event_data['output']:
                    if 'content' in output_item:
                        for content_item in output_item['content']:
                            if content_item.get('type') == 'output_text':
                                text = content_item.get('text', '')
                                if text and text.strip():
                                    workflow_message = {
                                        'type': 'assistant',
                                        'content': text,
                                        'timestamp': datetime.now().isoformat()
                                    }
                                    conversation_history.append(
                                        workflow_message)
                                    await self._broadcast(workflow_message)

            # Add 3 second pause before showing completion message
            await asyncio.sleep(3)

            # Send completion message
            completion_message = {
                'type': 'system',
                'content': '✅ Workflow completed! Check the generated_images folder for your marketing images.',
                'timestamp': datetime.now().isoformat()
            }
            conversation_history.append(completion_message)
            await self._broadcast(completion_message)

            # Clear pending request if workflow completed
            if not pending_requests['is_pending']:
                print(f"\n✅ Workflow completed\n")

    async def check_workflow_status(self, request: web.Request) -> web.Response:
        """Check if the workflow is available."""
        try:
            # Since we run workflow directly, just check if instance exists
            global workflow_instance
            if workflow_instance is not None:
                return web.json_response({'status': 'online', 'mode': 'direct'})
            else:
                return web.json_response({'status': 'offline', 'message': 'Workflow not initialized'}, status=503)
        except Exception as e:
            return web.json_response({'status': 'error', 'message': str(e)}, status=503)

    async def handle_message(self, request: web.Request) -> web.Response:
        """Handle incoming messages via HTTP POST."""
        try:
            data = await request.json()
            content = data.get('content', '').strip()

            print(
                f"\n✅ HTTP POST /api/message received with content: '{content}'")

            if content:
                await self.process_user_input(content)
                print(f"✅ HTTP POST /api/message - processed successfully")
                return web.json_response({'status': 'success'})

            return web.json_response({'status': 'error', 'message': 'No content provided'})
        except Exception as e:
            return web.json_response({'status': 'error', 'message': str(e)}, status=400)

    async def get_history(self, request: web.Request) -> web.Response:
        """Get conversation history."""
        return web.json_response(conversation_history)

    async def _broadcast(self, message: Dict[str, Any]):
        """Broadcast a message to all connected WebSocket clients."""
        disconnected = []
        for ws in active_connections:
            try:
                if not ws.closed:
                    await ws.send_json(message)
                else:
                    disconnected.append(ws)
            except Exception as e:
                # Only log if it's not a closing connection error
                if "closing" not in str(e).lower():
                    print(f'Error broadcasting to client: {e}')
                disconnected.append(ws)

        # Remove disconnected clients
        for ws in disconnected:
            if ws in active_connections:
                active_connections.remove(ws)


async def create_chat_ui_app(workflow_port: int = 8090) -> web.Application:
    """Create the chat UI application."""
    server = ChatUIServer()  # No longer needs workflow_port - runs workflow directly
    return server.app


def main():
    """Run the chat UI server."""
    current_dir = Path(__file__).parent
    root_dir = current_dir.parent

    env_paths = [root_dir / ".env", current_dir / ".env"]
    for env_path in env_paths:
        if env_path.exists():
            load_dotenv(env_path)
            break

    logging.basicConfig(level=logging.WARNING, format="%(message)s")

    # Suppress aiohttp access logs
    logging.getLogger('aiohttp.access').setLevel(logging.WARNING)

    print("=" * 80)
    print("🚀 Starting Chat UI server on http://localhost:8091")
    print("📦 Version: With WorkflowOutputEvent detection")
    print("=" * 80)

    async def init_app():
        app = await create_chat_ui_app()
        return app

    # Disable access log
    web.run_app(init_app(), host='localhost', port=8091, access_log=None)


if __name__ == "__main__":
    main()

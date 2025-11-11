# Copyright (c) Microsoft. All rights reserved.

from typing import Annotated
from pathlib import Path
from io import BytesIO
from dataclasses import dataclass
import os
import logging
import json
import base64
import asyncio
from azure.identity.aio import DefaultAzureCredential
from agent_framework_azure_ai import AzureAIAgentClient
from agent_framework import (
    AgentExecutor,
    AgentExecutorRequest,
    AgentExecutorResponse,
    AgentRunUpdateEvent,
    ChatMessage,
    Executor,
    FunctionCallContent,
    FunctionResultContent,
    RequestInfoEvent,
    response_handler,
    Role,
    ToolMode,
    Workflow,
    WorkflowBuilder,
    WorkflowContext,
    WorkflowEvent,
    WorkflowOutputEvent,
    handler,
)
import requests
from dotenv import load_dotenv
from openai import AzureOpenAI
from PIL import Image
from pydantic import Field
print("🔥 MARKETING.PY MODULE LOADING...")

# from azure.identity import AzureCliCredential
# from agent_framework.azure import AzureOpenAIChatClient

# Configure logger
logger = logging.getLogger(__name__)


# Load environment variables
# Load from parent directory first (root .env), then local
root_env = Path(__file__).parent.parent / ".env"
if root_env.exists():
    load_dotenv(root_env, override=True)
else:
    load_dotenv()

# Configuration for image generation
# Try new env var names first, fall back to old ones
IMAGE_ENDPOINT = os.getenv("IMAGE_ENDPOINT") or os.getenv(
    "AZURE_OPENAI_ENDPOINT", "")
IMAGE_API_KEY = os.getenv("IMAGE_API_KEY") or os.getenv(
    "AZURE_OPENAI_API_KEY", "")
IMAGE_MODEL_DEPLOYMENT = os.getenv("IMAGE_MODEL") or os.getenv(
    "AZURE_OPENAI_IMAGE_DEPLOYMENT_NAME", "dall-e-3")
DEBUG_SKIP_IMAGES = os.getenv("DEBUG_SKIP_IMAGES", "false").lower() == "true"


model_deployment_name = os.environ.get(
    "AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5", "gpt-4.1")

# Agent version handling - same pattern as chatkit_router.py
agent_version = os.environ.get("AZURE_AI_PROJECT_AGENT_VERSION", None)
if agent_version is not None and not agent_version.strip():
    agent_version = None

# # Helper function to get agent name with proper fallback
# def get_agent_name(fallback_name: str) -> str:
#     agent_id = os.environ.get("AZURE_AI_PROJECT_AGENT_ID", "")
#     return agent_id if agent_id.strip() else fallback_name


# chat_client = AzureOpenAIChatClient(api_key=os.environ.get("AZURE_OPENAI_API_KEY_GPT5"),
#                                     endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT_GPT5"),
#                                     deployment_name=os.environ.get("AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5"),
#                                     api_version=os.environ.get("AZURE_OPENAI_ENDPOINT_VERSION_GPT5", "2024-02-15-preview"))

print("🔧 Image Generation Config:")
print(
    f"   Endpoint: {IMAGE_ENDPOINT[:50]}..." if IMAGE_ENDPOINT else "   Endpoint: NOT SET")
print(f"   Model: {IMAGE_MODEL_DEPLOYMENT}")
print(
    f"   API Key: {'***' + IMAGE_API_KEY[-4:] if IMAGE_API_KEY else 'NOT SET'}")
print(f"   Debug Mode: {DEBUG_SKIP_IMAGES}")

# Setup image client and directory
image_client = AzureOpenAI(
    api_version="2024-02-01",
    api_key=IMAGE_API_KEY,
    azure_endpoint=IMAGE_ENDPOINT,
)

images_directory = Path(__file__).parent / "generated_images"
images_directory.mkdir(exist_ok=True)

"""
Sample: Multi-agent marketing workflow with creative tools and HITL

Pipeline layout:
campaign_planner_agent -> coordinator -> creative_agent (with tools) -> coordinator
-> coordinator.request_info() (HITL) -> coordinator.handle_draft_feedback()
-> creative_agent | localization_agent -> coordinator -> output

The campaign planner agent drafts marketing campaign briefs.
The creative agent generates social media images, videos, and captions using tools.
Human reviews the creatives and provides feedback via ctx.request_info().
The localization agent translates the approved content for target markets.

Demonstrates:
- Tool-enabled agent for creative generation (images and video)
- New ctx.request_info() + @response_handler pattern for HITL
- Multi-agent coordination and feedback loops
- Localization workflow

Prerequisites:
- Azure OpenAI configured for AzureOpenAIChatClient
- Run 'az login' before executing
"""

# Custom event to expose campaign planner responses


class CampaignPlannerResponseEvent(WorkflowEvent):
    """Event emitted when campaign planner produces a response."""

    def __init__(self, response_text: str):
        super().__init__(
            f"Campaign planner response: {response_text[:100]}...")
        self.response_text = response_text


# Custom event to expose localization agent responses
class LocalizationResponseEvent(WorkflowEvent):
    """Event emitted when localization agent produces a response."""

    def __init__(self, response_text: str):
        super().__init__(f"Localization response: {response_text[:100]}...")
        self.response_text = response_text


# Custom event to expose market selection question
class MarketSelectionQuestionEvent(WorkflowEvent):
    """Event emitted when asking user which markets to target."""

    def __init__(self, question_text: str):
        super().__init__("Market selection question")
        self.question_text = question_text


# Custom event to expose publishing schedule agent responses
class PublishingScheduleResponseEvent(WorkflowEvent):
    """Event emitted when publishing schedule agent produces a response."""

    def __init__(self, response_text: str):
        super().__init__(
            f"Publishing schedule response: {response_text[:100]}...")
        self.response_text = response_text


# Custom event to expose Instagram post preparation
class InstagramPostEvent(WorkflowEvent):
    """Event emitted when Instagram agent prepares a post for publishing."""

    def __init__(self, response_text: str):
        super().__init__(
            f"Instagram post prepared: {response_text[:100]}...")
        self.response_text = response_text


# Custom event to expose generated creative assets
class CreativeAssetsGeneratedEvent(WorkflowEvent):
    """Event emitted when creative assets (images/videos) are generated."""

    def __init__(self, assets: list):
        super().__init__(f"Generated {len(assets)} creative assets")
        self.assets = assets


def create_social_media_image(
    campaign_theme: Annotated[str, Field(description="The campaign theme or message for the image.")],
    style: Annotated[str, Field(description="Visual style (e.g., 'modern', 'minimalist', 'vibrant').")],
    caption: Annotated[str, Field(description="Compelling caption for this image (50-100 words).")],
    hashtags: Annotated[str, Field(description="3-5 relevant hashtags, e.g. '#innovation #tech #future'")],
) -> str:
    """Generate a social media image for the campaign using DALL-E."""
    import time

    timestamp = int(time.time())
    safe_theme = campaign_theme.replace(" ", "_").replace("/", "_")[:50]
    filename = f"social_image_{safe_theme}_{timestamp}.png"

    # DEBUG MODE: Skip actual image generation for faster testing
    if DEBUG_SKIP_IMAGES:
        image_path = images_directory / \
            f"{filename.replace('.png', '_DEBUG.png')}"

        # Create a simple placeholder image
        placeholder = Image.new('RGB', (1024, 1024), color=(200, 200, 200))
        placeholder.save(image_path)

        print(f"🐛 DEBUG MODE: Created placeholder image at {image_path}")

        # Return structured JSON with placeholder
        result_data = {
            "type": "image",
            "filename": str(image_path.name),
            "url": f"file://{image_path.absolute()}",
            "theme": campaign_theme,
            "style": style,
            "caption": caption,
            "hashtags": hashtags,
            "dimensions": "1024x1024px",
            "format": "PNG"
        }
        return json.dumps(result_data)

    # Create detailed DALL-E prompt
    image_prompt = f"Professional social media marketing image for {campaign_theme}. Style: {style}. High quality, engaging, suitable for Instagram/TikTok. No text overlay."

    print(f"🎨 Generating image with gpt-image-1-mini: {image_prompt[:100]}...")
    print(f"🎨 Using model: {IMAGE_MODEL_DEPLOYMENT}")
    print(f"🎨 Using endpoint: {IMAGE_ENDPOINT[:50]}...")

    try:
        # Generate image using DALL-E
        # Note: gpt-image-1-mini uses 'high'/'medium'/'low'/'auto' for quality, not 'standard'
        result = image_client.images.generate(
            model=IMAGE_MODEL_DEPLOYMENT,
            prompt=image_prompt,
            size="1024x1024",
            quality="high",
            n=1,
        )

        print("🎨 Image generation API call successful")

        # Extract and save the image
        json_response = json.loads(result.model_dump_json())
        image_path = images_directory / filename

        print(
            f"🎨 Response keys: {json_response.get('data', [{}])[0].keys() if json_response.get('data') else 'No data'}")

        # Handle b64_json response format (preferred)
        if "b64_json" in json_response["data"][0]:
            b64_data = json_response["data"][0]["b64_json"]
            image_data = base64.b64decode(b64_data)
            image = Image.open(BytesIO(image_data))
            image.save(image_path)
            print(f"✅ Image saved to {image_path}")
        elif "url" in json_response["data"][0]:
            # Fallback to URL format (requires requests library)
            try:
                image_url = json_response["data"][0]["url"]
                print(f"🎨 Downloading image from URL: {image_url[:50]}...")
                response = requests.get(image_url)
                if response.status_code == 200:
                    with open(image_path, "wb") as f:
                        f.write(response.content)
                    print(f"✅ Image downloaded and saved to {image_path}")
                else:
                    raise Exception(
                        f"Failed to download image from URL: {response.status_code}")
            except ImportError:
                raise Exception(
                    "requests library not installed - cannot download image from URL")
        else:
            raise Exception("No b64_json or url in API response")

        # Return structured JSON with real image path
        result_data = {
            "type": "image",
            "filename": str(image_path.name),
            "url": f"file://{image_path.absolute()}",
            "theme": campaign_theme,
            "style": style,
            "caption": caption,
            "hashtags": hashtags,
            "dimensions": "1024x1024px",
            "format": "PNG"
        }
        return json.dumps(result_data)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"❌ Error generating image: {e}")
        print(f"❌ Full traceback:\n{error_details}")
        # Return error info but still allow workflow to continue
        result_data = {
            "type": "image",
            "filename": "error.png",
            "url": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='400'%3E%3Crect width='400' height='400' fill='%23ffcccc'/%3E%3Ctext x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' font-family='Arial' font-size='16' fill='%23cc0000'%3EImage Generation Error%3C/text%3E%3C/svg%3E",
            "theme": campaign_theme,
            "style": style,
            "caption": caption,
            "hashtags": hashtags,
            "dimensions": "1024x1024px",
            "format": "PNG",
            "error": str(e)
        }
        return json.dumps(result_data)


def create_promotional_video(
    campaign_message: Annotated[str, Field(description="The key message or story for the video.")],
    caption: Annotated[str, Field(description="Compelling caption for this video (50-100 words).")],
    hashtags: Annotated[str, Field(description="3-5 relevant hashtags, e.g. '#innovation #tech #future'")],
    duration_seconds: Annotated[int, Field(
        description="Video duration in seconds (15-60).")] = 30,
) -> str:
    """Generate a promotional video for the campaign."""
    import time
    timestamp = int(time.time())
    safe_message = campaign_message.replace(" ", "_").replace("/", "_")[:50]
    filename = f"promo_video_{safe_message}_{timestamp}.mp4"

    # Return structured JSON with placeholder video thumbnail
    result_data = {
        "type": "video",
        "filename": filename,
        "url": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='400'%3E%3Crect width='400' height='400' fill='%23cccccc'/%3E%3Cpolygon points='150,100 150,300 300,200' fill='%23666'/%3E%3Ctext x='50%25' y='85%25' dominant-baseline='middle' text-anchor='middle' font-family='Arial' font-size='20' fill='%23666'%3EPromotional Video%3C/text%3E%3C/svg%3E",
        "message": campaign_message,
        "caption": caption,
        "hashtags": hashtags,
        "duration": f"{duration_seconds}s",
        "resolution": "1920x1080",
        "format": "MP4"
    }
    return json.dumps(result_data)


def post_to_ayrshare(
    post_content: Annotated[str, Field(description="The complete post text including caption and hashtags.")],
    media_urls: Annotated[list[str], Field(description="List of media URLs to include in the post. Can be local file paths (file://) or URLs.")],
    platforms: Annotated[list[str], Field(description="Target platforms (e.g., ['instagram', 'facebook', 'tiktok']).")],
    schedule_time: Annotated[str, Field(
        description="Optional: ISO format time to schedule the post. Leave empty for immediate posting.")] = "",
) -> str:
    """Post content to social media platforms using Ayrshare API.

    Automatically handles media upload for local files using Ayrshare's upload API.
    """

    # Get Ayrshare API key from environment
    ayrshare_api_key = os.environ.get("AYRSHARE_API_KEY")
    if not ayrshare_api_key:
        return json.dumps({
            "success": False,
            "error": "AYRSHARE_API_KEY environment variable not found",
            "message": "Please set your Ayrshare API key in the environment variables"
        })

    # Process media URLs - upload local files to Ayrshare
    uploaded_media_urls = []

    if media_urls:
        print(f"📁 Processing {len(media_urls)} media items...")

        for media_url in media_urls:
            if media_url.startswith("file://"):
                # Local file - needs to be uploaded
                file_path = media_url.replace("file://", "")

                try:
                    print(f"📤 Uploading local file: {file_path}")

                    # Check if file exists
                    from pathlib import Path
                    path = Path(file_path)
                    if not path.exists():
                        print(f"❌ File not found: {file_path}")
                        continue

                    # Prepare file for upload
                    with open(file_path, 'rb') as file:
                        files = {
                            'file': (path.name, file, f'image/{path.suffix[1:]}')
                        }

                        # Upload to Ayrshare media API
                        upload_response = requests.post(
                            "https://app.ayrshare.com/api/upload",
                            headers={
                                "Authorization": f"Bearer {ayrshare_api_key}"},
                            files=files,
                            timeout=60
                        )

                    if upload_response.status_code == 200:
                        upload_result = upload_response.json()
                        uploaded_url = upload_result.get("url")
                        if uploaded_url:
                            uploaded_media_urls.append(uploaded_url)
                            print(
                                f"✅ File uploaded successfully: {uploaded_url}")
                        else:
                            print(
                                f"❌ Upload succeeded but no URL returned for {file_path}")
                    else:
                        print(
                            f"❌ Failed to upload {file_path}: {upload_response.status_code}")
                        print(f"Response: {upload_response.text}")

                except Exception as e:
                    print(f"❌ Error uploading file {file_path}: {e}")
                    continue

            else:
                # Already a URL - use as-is
                uploaded_media_urls.append(media_url)
                print(f"🔗 Using existing URL: {media_url}")

    # Prepare the post payload
    payload = {
        "post": post_content,
        "platforms": platforms,
    }

    # Add media URLs if we have any
    if uploaded_media_urls:
        payload["mediaUrls"] = uploaded_media_urls
        print(f"📸 Including {len(uploaded_media_urls)} media items in post")

    # Add scheduling if provided
    if schedule_time:
        payload["scheduleDate"] = schedule_time

    try:
        print(f"🚀 Posting to Ayrshare API: {platforms}")
        print(f"📝 Post content: {post_content[:100]}...")

        # Make API request to Ayrshare
        response = requests.post(
            "https://app.ayrshare.com/api/post",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ayrshare_api_key}"
            },
            json=payload,
            timeout=30
        )

        # Parse response
        result = response.json()

        if response.status_code == 200:
            print(f"✅ Successfully posted to {platforms}")
            return json.dumps({
                "success": True,
                "platforms": platforms,
                "post_id": result.get("id"),
                "status": result.get("status"),
                "post_content": post_content,
                "media_urls": uploaded_media_urls,
                "media_count": len(uploaded_media_urls),
                "scheduled_time": schedule_time if schedule_time else "immediate",
                "ayrshare_response": result
            })
        else:
            print(f"❌ Ayrshare API error: {response.status_code}")
            return json.dumps({
                "success": False,
                "error": f"API request failed with status {response.status_code}",
                "message": result.get("message", "Unknown error"),
                "platforms": platforms,
                "ayrshare_response": result
            })

    except requests.exceptions.RequestException as e:
        print(f"❌ Network error posting to Ayrshare: {e}")
        return json.dumps({
            "success": False,
            "error": "Network error",
            "message": f"Failed to connect to Ayrshare API: {str(e)}",
            "platforms": platforms
        })
    except Exception as e:
        print(f"❌ Unexpected error posting to Ayrshare: {e}")
        return json.dumps({
            "success": False,
            "error": "Unexpected error",
            "message": str(e),
            "platforms": platforms
        })


@dataclass
class CampaignFollowupRequest:
    """Payload sent for campaign planner follow-up questions."""
    prompt: str = ""
    questions: str = ""


@dataclass
class DraftFeedbackRequest:
    """Payload sent for creative draft review."""
    prompt: str = ""
    draft_text: str = ""
    media_assets: list | None = None  # Store media assets for later use

    def __post_init__(self):
        if self.media_assets is None:
            self.media_assets = []


@dataclass
class MarketSelectionRequest:
    """Payload sent for market selection."""
    prompt: str = ""
    media_assets: list | None = None

    def __post_init__(self):
        if self.media_assets is None:
            self.media_assets = []


@dataclass
class ScheduleApprovalRequest:
    """Payload sent for publishing schedule approval."""
    prompt: str = ""
    schedule_text: str = ""


@dataclass
class LocalizedCaption:
    """A localized version of a media caption."""
    original_caption: str
    translated_caption: str
    language: str
    language_code: str  # e.g., "es", "fr", "de"


class Coordinator(Executor):
    """Bridge between the campaign planner, creative agent, localization, and publishing schedule.

    Handles human-in-the-loop approvals using ctx.request_info() and @response_handler."""

    def __init__(self, id: str, planner_id: str, creative_id: str, localization_id: str, publishing_id: str, instagram_id: str) -> None:
        super().__init__(id)
        self.planner_id = planner_id
        self.creative_id = creative_id
        self.localization_id = localization_id
        self.publishing_id = publishing_id
        self.instagram_id = instagram_id
        self.generated_assets = []  # Store generated creative assets
        self.target_markets = ""  # Store user-selected target markets
        print(f"🏗️  COORDINATOR CREATED: id='{id}', planner_id='{planner_id}'")

    @handler
    async def dispatch(
        self,
        message: ChatMessage,
        ctx: WorkflowContext[AgentExecutorRequest],
    ) -> None:
        """Handle initial campaign message and dispatch to campaign planner."""
        print("\n🚀 COORDINATOR DISPATCH METHOD CALLED!")
        print(f"🚀 Message type: {type(message)}")
        print(f"🚀 Message role: {message.role}")
        print(f"🚀 Message text: '{message.text[:100]}...'")
        print(f"🚀 Routing to planner_id: '{self.planner_id}'")

        # Send the message directly to campaign planner
        try:
            print(f"🚀 About to send message to target_id: '{self.planner_id}'")
            await ctx.send_message(
                AgentExecutorRequest(
                    messages=[message],
                    should_respond=True,
                ),
                target_id=self.planner_id,
            )
            print("🚀 Message sent to campaign planner successfully")
            print("🚀 Coordinator dispatch completed - now waiting for planner response")
        except Exception as e:
            print(f"❌ ERROR sending prompt to campaign planner: {e}")
            print(f"❌ Exception type: {type(e).__name__}")
            raise

    @handler
    async def on_agent_update(
        self,
        update: AgentRunUpdateEvent,
        ctx: WorkflowContext,
    ) -> None:
        """Capture tool outputs from creative agent during execution."""
        # Only process updates from creative agent
        if update.executor_id != self.creative_id:
            return

        print("\n🔧 AGENT UPDATE for creative_agent")
        logger.debug(" update type: {type(update).__name__}")

        print(f"🔧 DEBUG: update type: {type(update).__name__}")

        # AgentRunUpdateEvent should contain messages as they're produced
        # Access messages through the update object's attributes
        messages = getattr(update, 'messages', [])
        if messages:
            print(f"🔧 DEBUG: Found {len(messages)} messages in update")
            for msg_idx, msg in enumerate(messages):
                logger.debug(
                    " Message {msg_idx} - type: {type(msg).__name__}, role: {msg.role if hasattr(msg, 'role') else 'N/A'}")

                print(
                    f"🔧 DEBUG: Message {msg_idx} - type: {type(msg).__name__}, role: {msg.role if hasattr(msg, 'role') else 'N/A'}")

                if hasattr(msg, 'content'):
                    content = msg.content

                    # Handle content as list (multimodal messages with tool calls/results)
                    if isinstance(content, list):
                        logger.debug(
                            " Message {msg_idx} has list content with {len(content)} items")
                        print(
                            f"🔧 DEBUG: Message {msg_idx} has list content with {len(content)} items")
                        for item_idx, item in enumerate(content):
                            item_type = type(item).__name__
                            logger.debug("   Item {item_idx}: {item_type}")

                            print(f"🔧 DEBUG:   Item {item_idx}: {item_type}")

                            # Capture FunctionResultContent (tool outputs)
                            if isinstance(item, FunctionResultContent):
                                func_name = item.call_id if hasattr(
                                    item, 'call_id') else 'unknown'
                                print(
                                    f"✅✅✅ Found FunctionResultContent: {func_name}")
                                if hasattr(item, 'result') and item.result is not None:
                                    print(
                                        f"   Output preview: {item.result[:200]}")
                                    try:
                                        import json
                                        asset_data = json.loads(item.result)
                                        print(
                                            f"✅ Captured creative asset: {asset_data.get('type')} - {asset_data.get('filename')}")
                                        self.generated_assets.append(
                                            asset_data)
                                    except Exception as e:
                                        print(
                                            f"⚠️  Error parsing tool output: {e}")

                            # Also log FunctionCallContent for debugging
                            elif isinstance(item, FunctionCallContent):
                                func_name = item.name if hasattr(
                                    item, 'name') else 'unknown'
                                print(f"   📞 FunctionCallContent: {func_name}")

                    # Handle string content
                    elif isinstance(content, str):
                        preview = content[:100] if len(
                            content) > 100 else content
                        logger.debug(
                            " Message {msg_idx} string content: {preview}")
                        preview = content[:100] if len(
                            content) > 100 else content
                        print(
                            f"🔧 DEBUG: Message {msg_idx} string content: {preview}")
        else:
            logger.debug(" No messages in this update")

            print("🔧 DEBUG: No messages in this update")

        print(f"� Total assets captured: {len(self.generated_assets)}\n")

    @handler
    async def on_agent_response(
        self,
        draft: AgentExecutorResponse,
        ctx: WorkflowContext[CampaignFollowupRequest | DraftFeedbackRequest | MarketSelectionRequest | ScheduleApprovalRequest | AgentExecutorRequest, str],
    ) -> None:
        """Handle responses from agents - route to next agent or yield output."""

        print(
            f"\n🔍 DEBUG: on_agent_response called for executor_id: '{draft.executor_id}'")
        print("🔍 DEBUG: Expected IDs:")
        print(f"   - planner: '{self.planner_id}'")
        print(f"   - creative: '{self.creative_id}'")
        print(f"   - localization: '{self.localization_id}'")
        print(f"   - publishing: '{self.publishing_id}'")

        # Check if we have the agent run response
        if hasattr(draft, 'agent_run_response') and draft.agent_run_response:
            response_text_preview = draft.agent_run_response.text[:100] if hasattr(
                draft.agent_run_response, 'text') else "No text"
            print(f"🔍 DEBUG: Response preview: {response_text_preview}...")
        else:
            print("🔍 DEBUG: No agent_run_response found")

        # Add safety check to prevent infinite routing
        if draft.executor_id == "coordinator":
            print(
                "⚠️ WARNING: Ignoring response from coordinator itself to prevent loops")
            return

        # CAPTURE TOOL OUTPUTS FROM CREATIVE AGENT - WORKAROUND
        if draft.executor_id == self.creative_id:
            print("\n🎨 Creative agent response received - using file scan workaround")

            # WORKAROUND: Since tool outputs aren't accessible, scan for recently created files

            # import os
            import time
            from pathlib import Path

            images_dir = Path(__file__).parent / "generated_images"
            current_time = time.time()
            recent_threshold = 120  # Files created in last 2 minutes

            print(f"� Scanning {images_dir} for recent files...")

            if images_dir.exists():
                recent_files = []
                for file_path in images_dir.glob("social_image_*.png"):
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age < recent_threshold:
                        recent_files.append(file_path)
                        print(
                            f"   ✅ Found recent file: {file_path.name} (age: {file_age:.1f}s)")

                # Sort by modification time (newest first)
                recent_files.sort(
                    key=lambda f: f.stat().st_mtime, reverse=True)

                # Extract captions and hashtags from agent's text response

                agent_text = draft.agent_run_response.text if hasattr(
                    draft, 'agent_run_response') else ""
                import re
                agent_text = draft.agent_run_response.text if hasattr(
                    draft, 'agent_run_response') else ""
                print(f"Agent response: {agent_text}")

                # Parse captions in the specific format: "Image 1: caption text"
                captions = []
                hashtags_list = []

                # Look for "Image 1:", "Image 2:", "Video:" patterns
                image1_match = re.search(
                    r'Image 1:\s*(.+?)(?:\n|$)', agent_text, re.IGNORECASE)
                image2_match = re.search(
                    r'Image 2:\s*(.+?)(?:\n|$)', agent_text, re.IGNORECASE)
                video_match = re.search(
                    r'Video:\s*(.+?)(?:\n|$)', agent_text, re.IGNORECASE)

                if image1_match:
                    captions.append(image1_match.group(1).strip())
                if image2_match:
                    captions.append(image2_match.group(1).strip())
                if video_match:
                    captions.append(video_match.group(1).strip())

                print(f"Extracted {len(captions)} captions: {captions}")

                # Look for "Hashtags:" line
                hashtags_match = re.search(
                    r'Hashtags:\s*(.+?)(?:\n|$)', agent_text, re.IGNORECASE)
                if hashtags_match:
                    # Extract all hashtags from the line
                    hashtag_text = hashtags_match.group(1)
                    hashtag_matches = re.findall(r'#(\w+)', hashtag_text)
                    hashtags_list = [f"#{tag}" for tag in hashtag_matches]
                    print(f"Extracted hashtags: {hashtags_list}")

                # Default captions/hashtags if parsing failed
                if not captions:
                    print(
                        "WARNING: No captions found in agent response, using defaults")
                    captions = [
                        "Discover the power of our campaign!",
                        "Transform your experience!",
                        "Join the revolution!"
                    ]
                if not hashtags_list:
                    print(
                        "WARNING: No hashtags found in agent response, using defaults")
                    hashtags_list = ["#SocialMedia", "#Marketing", "#Launch"]

                # Create asset entries for the most recent files

                # Take up to 2 images
                for idx, file_path in enumerate(recent_files[:2]):
                    asset_data = {
                        "type": "image",
                        "filename": file_path.name,
                        "url": f"file://{file_path.absolute()}",
                        "caption": captions[idx] if idx < len(captions) else captions[0],
                        "hashtags": hashtags_list,
                        "dimensions": {"width": 1024, "height": 1024},
                        "format": "PNG"
                    }
                    self.generated_assets.append(asset_data)
                    print(f"   Added image: {asset_data['filename']}")
                    print(f"     Caption: {asset_data['caption']}")

                # Add video placeholder
                video_caption = captions[2] if len(
                    captions) > 2 else "Watch our latest campaign video!"
                video_asset = {
                    "type": "video",
                    "filename": "promo_video_campaign.mp4",
                    "url": "placeholder://video",
                    "caption": video_caption,
                    "hashtags": hashtags_list,
                    "duration": 30,
                    "format": "MP4"
                }
                self.generated_assets.append(video_asset)
                print(f"   Added video: {video_asset['filename']}")

            print(
                f"📊 Total creative assets captured: {len(self.generated_assets)}")
            for idx, asset in enumerate(self.generated_assets):
                print(
                    f"   {idx+1}. {asset.get('type')} - {asset.get('filename')}")

            # Emit event to send creative assets to frontend
            await ctx.add_event(CreativeAssetsGeneratedEvent(self.generated_assets))

            # Now send to HITL for review - do this explicitly here instead of falling through
            draft_text = draft.agent_run_response.text.strip()
            if not draft_text:
                draft_text = "No creative output was produced."

            prompt = (
                "Review the social media creatives and captions. Provide a short directional note "
                "(visual adjustments, caption tweaks, messaging changes, etc.). "
                "Keep it under 30 words. Type 'approve' to accept as-is."
            )

            # Use new request_info API instead of sending to RequestInfoExecutor
            await ctx.request_info(
                request_data=DraftFeedbackRequest(
                    prompt=prompt,
                    draft_text=draft_text,
                    media_assets=self.generated_assets
                ),
                response_type=str
            )
            return  # CRITICAL: Don't fall through to default handler

        if draft.executor_id == self.publishing_id:
            # Publishing schedule agent response; request human review
            schedule_response = draft.agent_run_response.text

            # Emit custom event so chat_ui can capture the schedule
            await ctx.add_event(PublishingScheduleResponseEvent(schedule_response))

            # Request human approval for the schedule using new request_info API
            prompt = (
                "Review the publishing schedule. Type 'approve' to accept and trigger Instagram publishing, or provide feedback for adjustments."
            )

            await ctx.request_info(
                request_data=ScheduleApprovalRequest(
                    prompt=prompt,
                    schedule_text=schedule_response
                ),
                response_type=str
            )
            return

        if draft.executor_id == self.instagram_id:
            # Instagram agent response; complete workflow
            instagram_response = draft.agent_run_response.text

            # Emit custom event so UI can capture the Instagram post data
            await ctx.add_event(InstagramPostEvent(instagram_response))

            # Complete the workflow
            print("📱 Instagram post prepared - workflow complete!")
            await ctx.yield_output(f"Campaign completed! Instagram post prepared:\n{instagram_response}")
            return

        if draft.executor_id == self.localization_id:
            # Localization agent response; route to publishing schedule agent
            localization_response = draft.agent_run_response.text

            # Emit custom event so chat_ui can capture the localization
            await ctx.add_event(LocalizationResponseEvent(localization_response))

            # Now route to publishing schedule agent
            print("🗓️ Routing to publishing schedule agent...")

            publishing_input = (
                "Create a 2-week social media publishing schedule for Instagram (posts and reels) "
                "and TikTok based on the campaign assets. Include optimal posting times and content types. "
                f"We have {len(self.generated_assets)} pieces of content to schedule.\n\n"
                f"Target markets selected by user: {self.target_markets}\n\n"
                "IMPORTANT: Create schedule entries for BOTH English (original) and the localized language(s) specified above.\n\n"
                "Return your response as a JSON array with this structure:\n"
                "[\n"
                '  {"date": "2025-11-01", "time": "09:00 AM", "platform": "Instagram", "type": "Post", "content": "Image 1 - Natural Beauty"},\n'
                '  {"date": "2025-11-01", "time": "06:00 PM", "platform": "TikTok", "type": "Video", "content": "Promotional Video"},\n'
                "  ...\n"
                "]\n"
            )

            await ctx.send_message(
                AgentExecutorRequest(
                    messages=[ChatMessage(Role.USER, text=publishing_input)],
                    should_respond=True,
                ),
                target_id=self.publishing_id,
            )
            return

        if draft.executor_id == self.planner_id:
            # Campaign planner finished - check if it's ready to proceed
            planner_response = draft.agent_run_response.text

            # Emit custom event so chat_ui can capture the response
            await ctx.add_event(CampaignPlannerResponseEvent(planner_response))

            # Print for debugging
            print(
                f"\n📋 Campaign Planner Response (Coordinator):\n{planner_response}\n")

            # Parse the JSON response to check final_plan flag
            import json
            try:
                response_data = json.loads(planner_response)
                final_plan = response_data.get('final_plan', False)

                if final_plan:
                    # Campaign plan is complete - proceed to creative agent
                    print("✅ Campaign plan complete - routing to creative agent")

                    await ctx.send_message(
                        AgentExecutorRequest(
                            messages=[ChatMessage(
                                Role.USER, text=planner_response)],
                            should_respond=True,
                        ),
                        target_id=self.creative_id,
                    )
                else:
                    # Campaign planner needs more info - wait for user response
                    print(
                        "⏸️ Campaign planner needs more information - waiting for user response")

                    # Extract the agent's question from the JSON response
                    agent_question = response_data.get(
                        'agent_response', 'Please provide more campaign details.')

                    # Request user input for the campaign planning questions
                    await ctx.request_info(
                        request_data=CampaignFollowupRequest(
                            prompt="Please answer the campaign planner's questions:",
                            questions=agent_question
                        ),
                        response_type=str
                    )
                    return

            except json.JSONDecodeError:
                # If not valid JSON, treat as incomplete and wait for user input
                print(
                    "⚠️ Campaign planner response is not valid JSON - waiting for user response")

                # Request user input for the campaign planning
                await ctx.request_info(
                    request_data=CampaignFollowupRequest(
                        prompt="The campaign planner's response was not in the expected format. Please provide more campaign details:",
                        questions=planner_response
                    ),
                    response_type=str
                )
                return

            return

        # If we reach here, it's an unexpected executor - log and ignore
        print(
            f"⚠️ WARNING: Unexpected executor response from '{draft.executor_id}'")
        print("⚠️ This might indicate incorrect workflow routing or missing handler logic")
        print(
            f"⚠️ Expected one of: {self.planner_id}, {self.creative_id}, {self.localization_id}, {self.publishing_id}")
        return

    @response_handler
    async def handle_campaign_followup(
        self,
        original_request: CampaignFollowupRequest,
        response: str,
        ctx: WorkflowContext[CampaignFollowupRequest | DraftFeedbackRequest | MarketSelectionRequest | ScheduleApprovalRequest | AgentExecutorRequest, str],
    ) -> None:
        """Handle responses to campaign planner follow-up questions."""
        note = (response or "").strip()
        print(f"📝 User answered campaign planner questions: {note}")

        # Send the user's answers back to the campaign planner
        await ctx.send_message(
            AgentExecutorRequest(
                messages=[ChatMessage(Role.USER, text=note)],
                should_respond=True,
            ),
            target_id=self.planner_id,
        )

    @response_handler
    async def handle_market_selection(
        self,
        original_request: MarketSelectionRequest,
        response: str,
        ctx: WorkflowContext[CampaignFollowupRequest | DraftFeedbackRequest | MarketSelectionRequest | ScheduleApprovalRequest | AgentExecutorRequest, str],
    ) -> None:
        """Handle market selection responses."""
        target_markets = (response or "").strip()
        self.target_markets = target_markets
        print(f"🌍 User selected target markets: {target_markets}")

        # Build content to translate with captions and hashtags
        content_to_translate = []
        for idx, asset in enumerate(self.generated_assets, 1):
            asset_type = asset.get('type', 'unknown')
            caption = asset.get('caption', '')
            hashtags = asset.get('hashtags', '')
            combined_text = f"{caption} {hashtags}"
            content_to_translate.append(
                f"Asset {idx} ({asset_type}): {combined_text}")

        localization_input = (
            f"Target markets: {target_markets}\n\n"
            "Translate the following social media content for the specified markets. "
            "Each line is one complete post with caption and hashtags:\n\n"
            + "\n".join(content_to_translate)
        )

        await ctx.send_message(
            AgentExecutorRequest(
                messages=[ChatMessage(Role.USER, text=localization_input)],
                should_respond=True,
            ),
            target_id=self.localization_id,
        )

    @response_handler
    async def handle_schedule_approval(
        self,
        original_request: ScheduleApprovalRequest,
        response: str,
        ctx: WorkflowContext[CampaignFollowupRequest | DraftFeedbackRequest | MarketSelectionRequest | ScheduleApprovalRequest | AgentExecutorRequest, str],
    ) -> None:
        """Handle publishing schedule approval responses."""
        note = (response or "").strip()

        if note.lower() == "approve":
            print("✅ Publishing schedule approved - triggering Instagram agent!")

            # Prepare detailed asset information for Instagram agent
            assets_info = []
            for asset in self.generated_assets:
                asset_info = {
                    "type": asset.get("type"),
                    "url": asset.get("url"),
                    "caption": asset.get("caption"),
                    "hashtags": asset.get("hashtags"),
                    "filename": asset.get("filename")
                }
                assets_info.append(asset_info)

            # Trigger Instagram agent with complete asset and schedule information
            instagram_input = (
                f"Campaign Assets ({len(self.generated_assets)} total):\n"
                + json.dumps(assets_info, indent=2) + "\n\n"
                f"Publishing Schedule:\n{original_request.schedule_text}\n\n"
                f"Target Markets: {self.target_markets}\n\n"
                "TASK: Select the FIRST Instagram post from the schedule and publish it using the post_to_ayrshare tool.\n\n"
                "INSTRUCTIONS:\n"
                "1. Find the first Instagram entry in the publishing schedule\n"
                "2. Extract the file paths (URLs starting with 'file://') from the campaign assets above\n"
                "3. Combine the asset captions and hashtags into complete post content\n"
                "4. Call post_to_ayrshare with the post content, file paths, and platform ['instagram']\n"
                "5. Return the publishing results as JSON\n\n"
                "The post_to_ayrshare tool will automatically upload the local image files and post to Instagram."
            )

            await ctx.send_message(
                AgentExecutorRequest(
                    messages=[ChatMessage(Role.USER, text=instagram_input)],
                    should_respond=True,
                ),
                target_id=self.instagram_id,
            )
        else:
            # User provided feedback on schedule - revise
            instruction = (
                "A human reviewer shared the following feedback on the "
                "publishing schedule:\n"
                f"{note or 'No specific guidance provided.'}\n\n"
                f"Previous schedule:\n{original_request.schedule_text}\n\n"
                "Revise the publishing schedule based on the feedback."
            )

            await ctx.send_message(
                AgentExecutorRequest(
                    messages=[ChatMessage(Role.USER, text=instruction)],
                    should_respond=True
                ),
                target_id=self.publishing_id,
            )

    @response_handler
    async def handle_draft_feedback(
        self,
        original_request: DraftFeedbackRequest,
        response: str,
        ctx: WorkflowContext[CampaignFollowupRequest | DraftFeedbackRequest | MarketSelectionRequest | ScheduleApprovalRequest | AgentExecutorRequest, str],
    ) -> None:
        """Handle responses to creative draft feedback.

        This method handles creative approval and feedback flows.
        """
        note = (response or "").strip()

        # This is creative approval (has media_assets)
        if note.lower() == "approve" and original_request.draft_text:
            # Human approved creative - now ask which markets to target
            print("✅ Creative approved - requesting target markets from user")

            # Ask user for target markets before localization
            market_prompt = "Which market(s) would you like to target?"

            # Emit event so chat_ui can capture this
            await ctx.add_event(MarketSelectionQuestionEvent(market_prompt))

            # Use new request_info API for market selection
            await ctx.request_info(
                request_data=MarketSelectionRequest(
                    prompt=market_prompt,
                    media_assets=self.generated_assets
                ),
                response_type=str
            )
            return

        # Human provided feedback on creatives; prompt creative agent to revise
        instruction = (
            "A human reviewer shared the following guidance:\n"
            f"{note or 'No specific guidance provided.'}\n\n"
            f"Previous creative work:\n{original_request.draft_text}\n\n"
            "Revise the social media creatives and captions based on the "
            "feedback. "
            "Regenerate images/video as needed and update captions accordingly."
        )

        await ctx.send_message(
            AgentExecutorRequest(
                messages=[ChatMessage(Role.USER, text=instruction)],
                should_respond=True
            ),
            target_id=self.creative_id,
        )


def get_workflow():
    """Create and return the workflow for DevUI.

    Returns a workflow that demonstrates multi-agent marketing with creative tools and human-in-the-loop feedback.
    The campaign planner creates a brief, the creative agent generates social media assets (images, video, captions),
    a human reviews and provides feedback, then the localization agent translates the approved content to Spanish.
    """

    print("🏗️  GET_WORKFLOW: Creating marketing workflow...")

    # from agent_framework import Workflow

    # Note: For AzureAIAgentClient, we use DefaultAzureCredential for authentication
    credential = DefaultAzureCredential()

    campaign_planner_agent = AgentExecutor(
        agent=AzureAIAgentClient(
            async_credential=credential,
            project_endpoint=os.environ.get("AZURE_AI_PROJECT_ENDPOINT"),
            model_deployment_name=model_deployment_name,
            agent_version=agent_version
        ).create_agent(
            name="campaign_planner_agent",
            instructions="""
You are a ** senior marketing strategist ** specializing in **social media campaign planning**, audience insights, and performance-driven content strategy. Your role is to create solid strategic foundations for **image and video–based social campaigns**.

**WORKFLOW APPROACH:**
Be efficient and decisive. Use smart defaults when information is missing rather than asking multiple follow-up questions. Only ask for clarification if the user's request is completely unclear.

**SMART DEFAULTS TO USE:**
- **Objective**: Brand awareness and engagement (if not specified)
- **Audience**: General demographic 18-45, tech-savvy social media users (if not specified)
- **Timeline**: 2-week campaign starting immediately (if not specified)
- **Platforms**: Instagram (Posts + Reels) and TikTok (if not specified)
- **Budget**: Mid-range social media budget (if not specified)

**CRITICAL OUTPUT FORMAT REQUIREMENT:**
All responses MUST be valid JSON using this exact structure:

{
  "agent_response": "your full message here",
  "campaign_title": "Short Campaign Name",
  "final_plan": false or true
}

**PREFERRED APPROACH:**
- On first interaction, create a complete campaign plan using the user's input + smart defaults
- Set `"final_plan": true` in most cases to move the workflow forward efficiently
- Include a concise `"campaign_title"` (3-6 words)
- Provide a strategic overview focusing on content themes, messaging, and creative direction

**ONLY set "final_plan": false if:**
- The user's request is completely unclear or contradictory
- You need ONE critical piece of information that cannot be reasonably assumed

**Example efficient response:**

{
  "agent_response": "Campaign Plan: Launch a 2-week social media campaign targeting tech-savvy millennials (18-35) focused on brand awareness and engagement. Content themes: Innovation showcase, behind-the-scenes, user testimonials. Platform strategy: Instagram Posts (product highlights), Instagram Reels (quick demos), TikTok Videos (trending format adoption). Posting frequency: 1 post daily, 3 reels/videos weekly. Success metrics: Engagement rate, reach, brand mention tracking. Handing off to Creative Agent for asset production.",
  "campaign_title": "Innovation Spotlight 2025",
  "final_plan": true
}

**DO NOT** ask multiple follow-up questions. Be decisive and use reasonable assumptions to create actionable plans quickly.
* If information is **complete**, set `"final_plan": true` and, in `"agent_response"`, provide a full strategic campaign plan and note the handoff to the Creative Agent.

**Example when incomplete: **


{
  "agent_response": "To build your social media campaign plan, I need a bit more information: 1. What are your main objectives? 2. Who is your target audience? 3. What is your budget range and timeline?",
  "final_plan": false
}


**Example when complete: **


{
  "agent_response": "Based on the details provided, here’s your complete social media campaign strategy using image and video content. [Insert detailed plan]. Handing off to Creative Agent.",
  "final_plan": true
}

""",
        ),
        id="campaign_planner_agent",
    )

    creative_agent = AgentExecutor(
        agent=AzureAIAgentClient(
            async_credential=credential,
            project_endpoint=os.environ.get("AZURE_AI_PROJECT_ENDPOINT"),
            model_deployment_name=model_deployment_name,
            agent_version=agent_version
        ).create_agent(
            name="creative_agent",
            instructions=(
                "You are a creative director who produces social media assets. "
                "Based on the campaign brief, create EXACTLY these 3 assets by calling the tools:\n\n"
                "REQUIRED TOOL CALLS:\n"
                "1. Call create_social_media_image with theme and style for Image 1\n"
                "2. Call create_social_media_image with theme and style for Image 2\n"
                "3. Call create_promotional_video with message and duration for Video 1\n\n"
                "IMPORTANT: After calling all 3 tools, respond with the captions you created in this EXACT format:\n"
                "Image 1: [caption for first image]\n"
                "Image 2: [caption for second image]\n"
                "Video: [caption for video]\n"
                "Hashtags: [list of hashtags]\n\n"
                "Example response:\n"
                "Image 1: Experience the thrill of all-weather running!\n"
                "Image 2: Stay dry, stay fast, stay unstoppable\n"
                "Video: Watch our runners conquer every condition\n"
                "Hashtags: #RunAnyWeather #AllWeatherPerformance #StayUnstoppable"
            ),
            tools=[create_social_media_image, create_promotional_video],
            tool_mode=ToolMode.AUTO,
        ),
        id="creative_agent",
    )

    localization_agent = AgentExecutor(
        agent=AzureAIAgentClient(
            async_credential=credential,
            project_endpoint=os.environ.get("AZURE_AI_PROJECT_ENDPOINT"),
            model_deployment_name=model_deployment_name,
            agent_version=agent_version
        ).create_agent(
            name="localization_agent",
            instructions=(
                "You are a localization specialist who translates marketing content for international markets. "
                "Your input will contain:\n"
                "1. Target markets: (e.g., 'Spain', 'Mexico', 'Latin America')\n"
                "2. Social media posts, each containing a caption and hashtags together\n\n"
                "TRANSLATION GUIDELINES BY MARKET:\n"
                "- Spain → Spanish (es-ES) with European conventions\n"
                "- Mexico → Spanish (es-MX) with Mexican conventions\n"
                "- Latin America → Spanish (es-LA) with neutral Latin American conventions\n"
                "- France → French (fr-FR)\n"
                "- Germany → German (de-DE)\n"
                "- Brazil → Portuguese (pt-BR)\n"
                "- If multiple markets specified, create translations for each\n\n"
                "CRITICAL: Return your response as a JSON array with one object per asset:\n"
                "[\n"
                "  {\n"
                '    "original": "full original text with caption and hashtags",\n'
                '    "translation": "texto completo traducido con título y hashtags",\n'
                '    "market": "Spain",\n'
                '    "language": "es-ES"\n'
                "  },\n"
                "  ...\n"
                "]\n\n"
                "Rules:\n"
                "- Keep caption and hashtags together in the translation\n"
                "- Translate hashtags appropriately for each market's audience\n"
                "- Preserve emojis and special characters\n"
                "- Maintain marketing tone and persuasiveness\n"
                "- Use market-appropriate terminology and conventions\n"
                "- Return ONLY the JSON array, no markdown code fences"
            ),
        ),
        id="localization_agent",
    )

    publishing_agent = AgentExecutor(
        agent=AzureAIAgentClient(
            async_credential=credential,
            project_endpoint=os.environ.get("AZURE_AI_PROJECT_ENDPOINT"),
            model_deployment_name=model_deployment_name,
            agent_version=agent_version
        ).create_agent(
            name="publishing_agent",
            instructions=(
                "You are a social media publishing strategist. Create optimal posting schedules for Instagram and TikTok.\n\n"
                "CRITICAL REQUIREMENTS:\n"
                "1. Return ONLY a JSON array - no other text, no markdown, no explanations\n"
                "2. Use EXACTLY these field names: platform, content_type, date, time, language, timezone, local_time, priority\n"
                "3. Do NOT use 'type' - use 'content_type'\n"
                "4. Do NOT use 'content' - use 'content_type'\n\n"
                "REQUIRED JSON FORMAT:\n"
                "[\n"
                '  {"platform": "Instagram", "content_type": "Post", "date": "2025-11-15", "time": "09:00 AM PST", "language": "English", "timezone": "PST", "local_time": null, "priority": "High"},\n'
                '  {"platform": "Instagram", "content_type": "Reel", "date": "2025-11-15", "time": "03:00 PM PST", "language": "English", "timezone": "PST", "local_time": null, "priority": "High"},\n'
                '  {"platform": "Instagram", "content_type": "Post", "date": "2025-11-16", "time": "10:00 AM PST", "language": "Spanish (Spain)", "timezone": "PST / CET", "local_time": "07:00 PM CET", "priority": "Medium"},\n'
                '  {"platform": "TikTok", "content_type": "Video", "date": "2025-11-16", "time": "12:00 PM PST", "language": "English", "timezone": "PST", "local_time": null, "priority": "Medium"}\n'
                "]\n\n"
                "FIELD SPECIFICATIONS:\n"
                "- platform: 'Instagram' or 'TikTok' (exactly as shown)\n"
                "- content_type: 'Post', 'Reel' (Instagram only), or 'Video' (TikTok)\n"
                "- date: YYYY-MM-DD format\n"
                "- time: HH:MM AM/PM PST format (always in PST for ALL posts)\n"
                "- language: 'English' or language/market from localization (e.g., 'Spanish (Spain)', 'Spanish (Mexico)', 'French (France)')\n"
                "- timezone: 'PST' for English posts, 'PST / [LOCAL_TZ]' for localized posts (e.g., 'PST / CET', 'PST / CST')\n"
                "- local_time: null for English posts, local timezone equivalent for localized posts (e.g., '07:00 PM CET')\n"
                "- priority: 'High', 'Medium', or 'Low'\n\n"
                "MARKET-SPECIFIC TIMEZONE MAPPINGS:\n"
                "- Spain: CET (PST + 9 hours)\n"
                "- Mexico: CST (PST + 2 hours)\n"
                "- France: CET (PST + 9 hours)\n"
                "- Germany: CET (PST + 9 hours)\n"
                "- Brazil: BRT (PST + 5 hours, or + 4 during daylight saving)\n"
                "- For general 'Latin America', use CST as default\n\n"
                "LOCALIZATION RULES:\n"
                "- Include both English and localized versions of each post based on the translations provided\n"
                "- English posts: time in PST only, timezone='PST', local_time=null\n"
                "- Localized posts: time in PST, timezone='PST / [appropriate timezone]', local_time shows equivalent local time\n"
                "- For localized posts, convert PST times to local timezone using the mappings above\n"
                "- Space localized posts to align with peak engagement times in target market (consider local evening hours)\n"
                "- If multiple markets are targeted, create separate schedule entries for each market's localized content\n\n"
                "Create 8-12 posts over 2 weeks, starting tomorrow. Include both English and all localized versions provided."
            ),
        ),
        id="publishing_agent",
    )

    instagram_agent = AgentExecutor(
        agent=AzureAIAgentClient(
            async_credential=credential,
            project_endpoint=os.environ.get("AZURE_AI_PROJECT_ENDPOINT"),
            model_deployment_name=model_deployment_name,
            agent_version=agent_version
        ).create_agent(
            name="instagram_agent",
            instructions=(
                "You are an Instagram publishing agent that uses the Ayrshare API to post content to Instagram.\n\n"
                "WORKFLOW:\n"
                "1. Extract the FIRST Instagram post from the provided publishing schedule\n"
                "2. Get the actual media file paths from the campaign assets (look for file:// URLs)\n"
                "3. Combine caption and hashtags into complete post content\n"
                "4. Use the post_to_ayrshare tool with the actual file paths (the tool will handle uploading)\n"
                "5. Return the posting results\n\n"
                "CRITICAL REQUIREMENTS:\n"
                "- Always use the post_to_ayrshare tool to publish the content\n"
                "- Target platform should be ['instagram']\n"
                "- Combine caption and hashtags into a single post_content string\n"
                "- Extract REAL file paths from campaign assets (not placeholder URLs)\n"
                "- Look for assets with 'url' field containing 'file://' paths\n"
                "- Post immediately (no scheduling)\n\n"
                "MEDIA URL EXTRACTION:\n"
                "The campaign assets contain entries like:\n"
                "{\n"
                '  "type": "image",\n'
                '  "url": "file:///path/to/social_image_1.png",\n'
                '  "caption": "Amazing content!",\n'
                '  "hashtags": ["#awesome", "#campaign"]\n'
                "}\n\n"
                "Extract the 'url' values that start with 'file://' and pass them to post_to_ayrshare.\n"
                "The tool will automatically upload these local files to Ayrshare and get public URLs.\n\n"
                "RESPONSE FORMAT:\n"
                "After posting, return a JSON summary with these fields:\n"
                "{\n"
                '  "post_id": "generated_post_id",\n'
                '  "platform": "Instagram",\n'
                '  "status": "published" or "failed",\n'
                '  "post_content": "Full caption with hashtags",\n'
                '  "media_urls": ["uploaded_url1", "uploaded_url2"],\n'
                '  "ayrshare_response": {...},\n'
                '  "published_at": "timestamp",\n'
                '  "success": true/false\n'
                "}\n\n"
                "EXAMPLE WORKFLOW:\n"
                "1. Find first Instagram post in schedule\n"
                "2. Extract media file paths: ['file:///workspace/app/agents/src/zava_shop_agents/generated_images/social_image_1.png']\n"
                "3. Combine: 'Amazing product launch! 🚀 Join the revolution #innovation #tech #launch'\n"
                "4. Call: post_to_ayrshare(post_content, file_paths, ['instagram'])\n"
                "5. Return results\n\n"
                "ALWAYS use the post_to_ayrshare tool - this agent ACTUALLY POSTS to Instagram!"
            ),
            tools=[post_to_ayrshare],
            tool_choice=ToolMode.AUTO,
        ),
        id="instagram_agent",
    )

    # No longer need RequestInfoExecutor nodes - using ctx.request_info() instead
    print("🏗️  GET_WORKFLOW: Creating Coordinator instance...")
    coordinator = Coordinator(
        id="coordinator",
        planner_id=campaign_planner_agent.id,
        creative_id=creative_agent.id,
        localization_id=localization_agent.id,
        publishing_id=publishing_agent.id,
        instagram_id=instagram_agent.id,
    )
    print("🏗️  GET_WORKFLOW: Coordinator instance created!")

    # Build the workflow with name and description for DevUI
    # Note: HITL interactions now handled via ctx.request_info() in Coordinator
    print("🏗️  GET_WORKFLOW: Building workflow with start_executor...")
    workflow: Workflow = (
        WorkflowBuilder(
            name="Marketing Campaign with Creative Tools and HITL",
            description="Coordinator routes initial request to campaign planner → creative agent (images/video) → "
            "human review → market selection → localization → "
            "publishing schedule → human approval. Multi-stage "
            "HITL workflow using ctx.request_info() pattern."
        )
        .set_start_executor(coordinator)
        .add_edge(coordinator, campaign_planner_agent)
        .add_edge(campaign_planner_agent, coordinator)
        .add_edge(coordinator, creative_agent)
        .add_edge(creative_agent, coordinator)
        .add_edge(coordinator, localization_agent)
        .add_edge(localization_agent, coordinator)
        .add_edge(coordinator, publishing_agent)
        .add_edge(publishing_agent, coordinator)
        .add_edge(coordinator, instagram_agent)
        .add_edge(instagram_agent, coordinator)
        .build()
    )
    print("🏗️  GET_WORKFLOW: Workflow built successfully!")

    return workflow


async def main() -> None:
    """Run the workflow with creative tools and human feedback."""
    workflow = get_workflow()

    print("Interactive mode. When prompted, provide feedback or type 'approve' to accept the social media creatives.\n")

    # Run workflow with human-in-the-loop using streaming
    pending_responses: dict[str, str] | None = None
    completed = False

    while not completed:
        # Stream workflow execution
        stream = (
            workflow.send_responses_streaming(pending_responses)
            if pending_responses is not None
            else workflow.run_stream(
                "**Campaign:** #RunYourWay — Launch of StrideX running shoes to boost awareness and sales.\n"
                "**Audience:** Active adults 18–40 passionate about fitness and performance gear.\n"
                "**Platforms & Content:** Instagram, TikTok, YouTube — challenge videos, athlete collabs, UGC runs.\n"
                "**Goal:** 10K site visits, 1K purchases, 2K hashtag uses in first month."
                "**Timeline** 4 weeks"
                "**Budget** 10k"
            )
        )
        pending_responses = None
        requests: list[tuple[str, CampaignFollowupRequest | DraftFeedbackRequest |
                             MarketSelectionRequest | ScheduleApprovalRequest]] = []

        # Process events from the stream
        async for event in stream:
            # Capture human feedback requests for all request types
            if isinstance(event, RequestInfoEvent):
                request_data = event.data
                if isinstance(request_data, (CampaignFollowupRequest, DraftFeedbackRequest, MarketSelectionRequest, ScheduleApprovalRequest)):
                    requests.append((event.request_id, request_data))
            # Capture workflow output
            elif isinstance(event, WorkflowOutputEvent):
                print(f"\n===== Final Result =====\n{event.data}\n")
                completed = True

        # If we have requests, prompt the user
        if requests and not completed:
            responses: dict[str, str] = {}
            for request_id, request in requests:
                # Handle different request types appropriately
                if isinstance(request, CampaignFollowupRequest):
                    print("\n----- Campaign Planning Questions -----")
                    print(request.questions.strip())
                    print(f"\n{request.prompt}")
                elif isinstance(request, DraftFeedbackRequest):
                    print("\n----- Social Media Creatives -----")
                    print(request.draft_text.strip())
                    print(f"\n{request.prompt}")
                elif isinstance(request, MarketSelectionRequest):
                    print("\n----- Market Selection -----")
                    print(f"\n{request.prompt}")
                elif isinstance(request, ScheduleApprovalRequest):
                    print("\n----- Publishing Schedule -----")
                    print(request.schedule_text.strip())
                    print(f"\n{request.prompt}")

                answer = input("Your response: ").strip()  # noqa: ASYNC250
                if answer.lower() == "exit":
                    print("Exiting...")
                    return
                responses[request_id] = answer
            pending_responses = responses

    print("Workflow complete!")


if __name__ == "__main__":
    asyncio.run(main())

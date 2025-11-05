# Copyright (c) Microsoft. All rights reserved.

import asyncio
import base64
import json
import os
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Annotated

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
    RequestInfoExecutor,
    RequestInfoMessage,
    RequestResponse,
    Role,
    ToolMode,
    WorkflowBuilder,
    WorkflowContext,
    WorkflowEvent,
    WorkflowOutputEvent,
    handler,
)
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import AzureCliCredential
from dotenv import load_dotenv
from openai import AzureOpenAI
from PIL import Image
from pydantic import Field

# Load environment variables
# Load from parent directory first (root .env), then local
root_env = Path(__file__).parent.parent / ".env"
if root_env.exists():
    load_dotenv(root_env, override=True)
else:
    load_dotenv()

# Configuration for image generation
# Try new env var names first, fall back to old ones
IMAGE_ENDPOINT = os.getenv("IMAGE_ENDPOINT") or os.getenv("AZURE_OPENAI_ENDPOINT", "")
IMAGE_API_KEY = os.getenv("IMAGE_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY", "")
IMAGE_MODEL_DEPLOYMENT = os.getenv("IMAGE_MODEL") or os.getenv("AZURE_OPENAI_IMAGE_DEPLOYMENT_NAME", "dall-e-3")
DEBUG_SKIP_IMAGES = os.getenv("DEBUG_SKIP_IMAGES", "false").lower() == "true"

print(f"🔧 Image Generation Config:")
print(f"   Endpoint: {IMAGE_ENDPOINT[:50]}..." if IMAGE_ENDPOINT else "   Endpoint: NOT SET")
print(f"   Model: {IMAGE_MODEL_DEPLOYMENT}")
print(f"   API Key: {'***' + IMAGE_API_KEY[-4:] if IMAGE_API_KEY else 'NOT SET'}")
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
-> hitl_review (HITL) -> coordinator -> creative_agent | localization_agent -> coordinator -> output

The campaign planner agent drafts marketing campaign briefs.
The creative agent generates social media images, videos, and captions using tools.
Human reviews the creatives and provides feedback.
The localization agent translates the approved content to Spanish.

Demonstrates:
- Tool-enabled agent for creative generation (images and video)
- RequestInfoExecutor for human-in-the-loop approval  
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
        super().__init__(f"Campaign planner response: {response_text[:100]}...")
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
        super().__init__(f"Publishing schedule response: {response_text[:100]}...")
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
        image_path = images_directory / f"{filename.replace('.png', '_DEBUG.png')}"
        
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
        
        print(f"🎨 Image generation API call successful")
        
        # Extract and save the image
        json_response = json.loads(result.model_dump_json())
        image_path = images_directory / filename
        
        print(f"🎨 Response keys: {json_response.get('data', [{}])[0].keys() if json_response.get('data') else 'No data'}")
        
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
                import requests
                image_url = json_response["data"][0]["url"]
                print(f"🎨 Downloading image from URL: {image_url[:50]}...")
                response = requests.get(image_url)
                if response.status_code == 200:
                    with open(image_path, "wb") as f:
                        f.write(response.content)
                    print(f"✅ Image downloaded and saved to {image_path}")
                else:
                    raise Exception(f"Failed to download image from URL: {response.status_code}")
            except ImportError:
                raise Exception("requests library not installed - cannot download image from URL")
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
    duration_seconds: Annotated[int, Field(description="Video duration in seconds (15-60).")] = 30,
) -> str:
    """Generate a promotional video for the campaign."""
    import time
    import json
    timestamp = int(time.time())
    filename = f"promo_video_{timestamp}.mp4"
    
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



@dataclass
class DraftFeedbackRequest(RequestInfoMessage):
    """Payload sent for human review."""
    prompt: str = ""
    draft_text: str = ""
    media_assets: list = None  # Store media assets for later use
    
    def __post_init__(self):
        if self.media_assets is None:
            self.media_assets = []


@dataclass
class LocalizedCaption:
    """A localized version of a media caption."""
    original_caption: str
    translated_caption: str
    language: str
    language_code: str  # e.g., "es", "fr", "de"


class Coordinator(Executor):
    """Bridge between the campaign planner, creative agent, human feedback, localization, and publishing schedule."""

    def __init__(self, id: str, planner_id: str, creative_id: str, hitl_review_id: str, localization_id: str, publishing_id: str, final_hitl_approval_id: str) -> None:
        super().__init__(id)
        self.planner_id = planner_id
        self.creative_id = creative_id
        self.hitl_review_id = hitl_review_id
        self.localization_id = localization_id
        self.publishing_id = publishing_id
        self.final_hitl_approval_id = final_hitl_approval_id
        self.generated_assets = []  # Store generated creative assets
        self.target_markets = ""  # Store user-selected target markets

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
        
        print(f"\n🔧 AGENT UPDATE for creative_agent")
        print(f"🔧 DEBUG: update type: {type(update).__name__}")
        
        # AgentRunUpdateEvent should contain messages as they're produced
        if hasattr(update, 'messages') and update.messages:
            print(f"🔧 DEBUG: Found {len(update.messages)} messages in update")
            for msg_idx, msg in enumerate(update.messages):
                print(f"🔧 DEBUG: Message {msg_idx} - type: {type(msg).__name__}, role: {msg.role if hasattr(msg, 'role') else 'N/A'}")
                
                if hasattr(msg, 'content'):
                    content = msg.content
                    
                    # Handle content as list (multimodal messages with tool calls/results)
                    if isinstance(content, list):
                        print(f"🔧 DEBUG: Message {msg_idx} has list content with {len(content)} items")
                        for item_idx, item in enumerate(content):
                            item_type = type(item).__name__
                            print(f"🔧 DEBUG:   Item {item_idx}: {item_type}")
                            
                            # Capture FunctionResultContent (tool outputs)
                            if isinstance(item, FunctionResultContent):
                                func_name = item.name if hasattr(item, 'name') else 'unknown'
                                print(f"✅✅✅ Found FunctionResultContent: {func_name}")
                                if hasattr(item, 'output'):
                                    print(f"   Output preview: {item.output[:200]}")
                                    try:
                                        import json
                                        asset_data = json.loads(item.output)
                                        print(f"✅ Captured creative asset: {asset_data.get('type')} - {asset_data.get('filename')}")
                                        self.generated_assets.append(asset_data)
                                    except Exception as e:
                                        print(f"⚠️  Error parsing tool output: {e}")
                            
                            # Also log FunctionCallContent for debugging
                            elif isinstance(item, FunctionCallContent):
                                func_name = item.name if hasattr(item, 'name') else 'unknown'
                                print(f"   📞 FunctionCallContent: {func_name}")
                    
                    # Handle string content
                    elif isinstance(content, str):
                        preview = content[:100] if len(content) > 100 else content
                        print(f"🔧 DEBUG: Message {msg_idx} string content: {preview}")
        else:
            print(f"🔧 DEBUG: No messages in this update")
        
        print(f"� Total assets captured: {len(self.generated_assets)}\n")
    
    @handler
    async def on_agent_response(
        self,
        draft: AgentExecutorResponse,
        ctx: WorkflowContext[DraftFeedbackRequest, str],
    ) -> None:
        """Handle responses from agents - route to next agent or yield output."""
        
        print(f"\n🔍 DEBUG: on_agent_response called for executor_id: {draft.executor_id}")
        
        # CAPTURE TOOL OUTPUTS FROM CREATIVE AGENT - WORKAROUND
        if draft.executor_id == self.creative_id:
            print(f"\n🎨 Creative agent response received - using file scan workaround")
            
            # WORKAROUND: Since tool outputs aren't accessible, scan for recently created files
            import os
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
                        print(f"   ✅ Found recent file: {file_path.name} (age: {file_age:.1f}s)")
                
                # Sort by modification time (newest first)
                recent_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
                
                # Extract captions and hashtags from agent's text response
                import re
                agent_text = draft.agent_run_response.text if hasattr(draft, 'agent_run_response') else ""
                print(f"Agent response: {agent_text}")
                
                # Parse captions in the specific format: "Image 1: caption text"
                captions = []
                hashtags_list = []
                
                # Look for "Image 1:", "Image 2:", "Video:" patterns
                image1_match = re.search(r'Image 1:\s*(.+?)(?:\n|$)', agent_text, re.IGNORECASE)
                image2_match = re.search(r'Image 2:\s*(.+?)(?:\n|$)', agent_text, re.IGNORECASE)
                video_match = re.search(r'Video:\s*(.+?)(?:\n|$)', agent_text, re.IGNORECASE)
                
                if image1_match:
                    captions.append(image1_match.group(1).strip())
                if image2_match:
                    captions.append(image2_match.group(1).strip())
                if video_match:
                    captions.append(video_match.group(1).strip())
                
                print(f"Extracted {len(captions)} captions: {captions}")
                
                # Look for "Hashtags:" line
                hashtags_match = re.search(r'Hashtags:\s*(.+?)(?:\n|$)', agent_text, re.IGNORECASE)
                if hashtags_match:
                    # Extract all hashtags from the line
                    hashtag_text = hashtags_match.group(1)
                    hashtag_matches = re.findall(r'#(\w+)', hashtag_text)
                    hashtags_list = [f"#{tag}" for tag in hashtag_matches]
                    print(f"Extracted hashtags: {hashtags_list}")
                
                # Default captions/hashtags if parsing failed
                if not captions:
                    print("WARNING: No captions found in agent response, using defaults")
                    captions = [
                        "Discover the power of our campaign!",
                        "Transform your experience!",
                        "Join the revolution!"
                    ]
                if not hashtags_list:
                    print("WARNING: No hashtags found in agent response, using defaults")
                    hashtags_list = ["#SocialMedia", "#Marketing", "#Launch"]
                
                # Create asset entries for the most recent files
                
                for idx, file_path in enumerate(recent_files[:2]):  # Take up to 2 images
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
                video_caption = captions[2] if len(captions) > 2 else "Watch our latest campaign video!"
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
            
            print(f"📊 Total creative assets captured: {len(self.generated_assets)}")
            for idx, asset in enumerate(self.generated_assets):
                print(f"   {idx+1}. {asset.get('type')} - {asset.get('filename')}")
            
            # Now send to HITL for review - do this explicitly here instead of falling through
            draft_text = draft.agent_run_response.text.strip()
            if not draft_text:
                draft_text = "No creative output was produced."

            prompt = (
                "Review the social media creatives and captions. Provide a short directional note "
                "(visual adjustments, caption tweaks, messaging changes, etc.). "
                "Keep it under 30 words. Type 'approve' to accept as-is."
            )
            
            await ctx.send_message(
                DraftFeedbackRequest(
                    prompt=prompt, 
                    draft_text=draft_text,
                    media_assets=self.generated_assets
                ),
                target_id=self.hitl_review_id,
            )
            return  # CRITICAL: Don't fall through to default handler
        
        if draft.executor_id == self.publishing_id:
            # Publishing schedule agent response; request human review
            schedule_response = draft.agent_run_response.text
            
            # Emit custom event so chat_ui can capture the schedule
            await ctx.add_event(PublishingScheduleResponseEvent(schedule_response))
            
            # Request human approval for the schedule
            prompt = (
                "Review the publishing schedule. Type 'approve' to accept or provide feedback for adjustments."
            )
            
            await ctx.send_message(
                DraftFeedbackRequest(
                    prompt=prompt,
                    draft_text=schedule_response,
                    media_assets=[]
                ),
                target_id=self.final_hitl_approval_id,
            )
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
            print(f"\n📋 Campaign Planner Response (Coordinator):\n{planner_response}\n")
            
            # Parse the JSON response to check final_plan flag
            try:
                import json
                response_data = json.loads(planner_response)
                final_plan = response_data.get('final_plan', False)
                
                if final_plan:
                    # Campaign plan is complete - proceed to creative agent
                    print("✅ Campaign plan complete - routing to creative agent")
                    
                    # # Generate creative assets directly by calling the tools
                    # print("🎨 Generating creative assets...")
                    # import json
                    
                    # # Generate 2 images and 1 video
                    # asset1_json = create_social_media_image(
                    #     campaign_theme="GlowLeaf Moisturizer - Natural Beauty",
                    #     style="modern minimalist",
                    #     caption="Discover your natural glow with GlowLeaf Moisturizer ✨ Eco-friendly skincare that loves your skin and the planet 🌿",
                    #     hashtags="#GlowNaturally #EcoBeauty #GlowLeaf #SustainableSkincare #NaturalGlow"
                    # )
                    # asset1 = json.loads(asset1_json)
                    
                    # asset2_json = create_social_media_image(
                    #     campaign_theme="GlowLeaf Moisturizer - Lifestyle",
                    #     style="vibrant lifestyle",
                    #     caption="Morning routine essentials 🌅 Start your day with GlowLeaf and embrace radiant, healthy skin naturally 💚",
                    #     hashtags="#MorningRoutine #GlowLeaf #HealthySkin #GreenBeauty #SelfCare"
                    # )
                    # asset2 = json.loads(asset2_json)
                    
                    # asset3_json = create_promotional_video(
                    #     campaign_message="Experience the power of nature with GlowLeaf Moisturizer",
                    #     caption="From nature to your skin 🌱 Watch how GlowLeaf transforms your skincare routine with sustainable, effective ingredients ✨",
                    #     hashtags="#GlowLeaf #GlowNaturally #EcoSkincare #GreenBeauty",
                    #     duration_seconds=30
                    # )
                    # asset3 = json.loads(asset3_json)
                    
                    # # Emit event with all generated assets
                    # generated_assets = [asset1, asset2, asset3]
                    # self.generated_assets = generated_assets  # Store for later use
                    # await ctx.add_event(CreativeAssetsGeneratedEvent(assets=generated_assets))
                    # print(f"✅ Generated {len(generated_assets)} creative assets")
                    
                    await ctx.send_message(
                        AgentExecutorRequest(
                            messages=[ChatMessage(Role.USER, text=planner_response)],
                            should_respond=True,
                        ),
                        target_id=self.creative_id,
                    )
                else:
                    # Campaign planner needs more info - wait for user response
                    # The workflow will pause here and wait for user input via send_responses
                    print("⏸️ Campaign planner needs more information - waiting for user response")
                    # Don't send any message - workflow will wait for external input
                    
            except json.JSONDecodeError:
                # If not valid JSON, treat as incomplete and wait for user input
                print("⚠️ Campaign planner response is not valid JSON - waiting for user response")
            
            return
        
        # If we reach here, it's an unexpected executor - log and ignore
        print(f"⚠️ WARNING: Unexpected executor response: {draft.executor_id}")

    @handler
    async def on_human_feedback(
        self,
        feedback: RequestResponse[DraftFeedbackRequest, str],
        ctx: WorkflowContext[AgentExecutorRequest, str],
    ) -> None:
        """Process human feedback and route accordingly."""
        note = (feedback.data or "").strip()
        original = feedback.original_request
        request_id = feedback.request_id
        
        # Check if this is schedule approval (no media_assets means it's the schedule review)
        if not original.media_assets or len(original.media_assets) == 0:
            if note.lower() == "approve":
                # Schedule approved - complete workflow
                print("✅ Publishing schedule approved - workflow complete!")
                await ctx.yield_output(original.draft_text)
            else:
                # User provided feedback on schedule - revise
                instruction = (
                    "A human reviewer shared the following feedback on the publishing schedule:\n"
                    f"{note or 'No specific guidance provided.'}\n\n"
                    f"Previous schedule:\n{original.draft_text}\n\n"
                    "Revise the publishing schedule based on the feedback."
                )
                
                await ctx.send_message(
                    AgentExecutorRequest(
                        messages=[ChatMessage(Role.USER, text=instruction)],
                        should_respond=True
                    ),
                    target_id=self.publishing_id,
                )
            return
        
        # This is creative approval (has media_assets)
        if note.lower() == "approve" and original.draft_text:
            # Human approved creative - now ask which markets to target
            print("✅ Creative approved - requesting target markets from user")
            
            # Ask user for target markets before localization
            market_prompt = "Which market(s) would you like to target?"
            
            # Emit event so chat_ui can display this as coming from localization agent
            await ctx.add_event(MarketSelectionQuestionEvent(market_prompt))
            
            await ctx.send_message(
                DraftFeedbackRequest(
                    prompt=market_prompt,
                    draft_text="",  # No draft to show, just asking for input
                    media_assets=self.generated_assets  # Keep assets for next step
                ),
                target_id=self.hitl_review_id,
            )
            return

        # If draft_text is empty and we have media_assets, this is market selection response
        if self.generated_assets and not original.draft_text:
            # This is the market selection response
            target_markets = note.strip()
            self.target_markets = target_markets  # Store for publishing agent
            print(f"🌍 User selected target markets: {target_markets}")
            
            # Build content to translate with captions and hashtags
            content_to_translate = []
            
            for idx, asset in enumerate(self.generated_assets, 1):
                asset_type = asset.get('type', 'unknown')
                caption = asset.get('caption', '')
                hashtags = asset.get('hashtags', '')
                
                # Combine caption and hashtags for this asset
                combined_text = f"{caption} {hashtags}"
                content_to_translate.append(f"Asset {idx} ({asset_type}): {combined_text}")
            
            localization_input = (
                f"Target markets: {target_markets}\n\n"
                "Translate the following social media content for the specified markets. "
                "Each line is one complete post with caption and hashtags:\n\n" + 
                "\n".join(content_to_translate)
            )
            
            print(f"🌍 Sending content to localization agent:\n{localization_input}\n")
            
            await ctx.send_message(
                AgentExecutorRequest(
                    messages=[ChatMessage(Role.USER, text=localization_input)],
                    should_respond=True,
                ),
                target_id=self.localization_id,
            )
            return

        # Human provided feedback on creatives; prompt the creative agent to revise.
        instruction = (
            "A human reviewer shared the following guidance:\n"
            f"{note or 'No specific guidance provided.'}\n\n"
            f"Previous creative work:\n{original.draft_text}\n\n"
            "Revise the social media creatives and captions based on the feedback. "
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
    from agent_framework import Workflow
    
    chat_client = AzureOpenAIChatClient(credential=AzureCliCredential())

    campaign_planner_agent = AgentExecutor(
        agent=chat_client.create_agent(
            name="campaign_planner_agent",
            instructions="""Here’s a concise, rewritten version of your instruction — narrowed to focus on **social media campaigns using images and video**, and requiring slightly less information while keeping the JSON format rule intact:

---

You are a **senior marketing strategist** specializing in **social media campaign planning**, audience insights, and performance-driven content strategy. Your role is to create solid strategic foundations for **image and video–based social campaigns**.

**CRITICAL WORKFLOW RULE:**
You must collect all essential information before delivering a final campaign plan. If key details are missing, ask focused clarifying questions and wait for responses.

**Essential Information Required:**

1. Campaign objectives and goals
2. Target audience (demographics and psychographics)
3. Budget range and campaign timeline
4. Preferred social media platforms
5. Key metrics for measuring success

**CRITICAL OUTPUT FORMAT REQUIREMENT:**
All responses MUST be valid JSON using this exact structure:


All responses MUST be valid JSON using this exact structure:


{
  "agent_response": "your full message here",
  "campaign_title": "Short Campaign Name",
  "final_plan": false or true
}


**DO NOT** return plain text or markdown — only valid JSON.

**Response Guidelines:**

* If information is **incomplete**, set `"final_plan": false`, omit `"campaign_title"`, and in `"agent_response"`, ask specific clarifying questions.
* If information is **complete**, set `"final_plan": true`, include a short `"campaign_title"` (3-6 words), and in `"agent_response"`, provide a full strategic campaign plan and note the handoff to the Creative Agent.

**Example when incomplete:**


{
  "agent_response": "To build your social media campaign plan, I need a bit more information: 1. What are your main objectives? 2. Who is your target audience? 3. What is your budget range and timeline?",
  "final_plan": false
}


**Example when complete:**


{
  "agent_response": "Based on the details provided, here's your complete social media campaign strategy using image and video content. [Insert detailed plan]. Handing off to Creative Agent.",
  "campaign_title": "EcoGlow Spring Launch",
  "final_plan": true
}


**DO NOT** return plain text or markdown — only valid JSON.

**Response Guidelines:**

* If information is **incomplete**, set `"final_plan": false` and, in `"agent_response"`, ask specific clarifying questions.
* If information is **complete**, set `"final_plan": true` and, in `"agent_response"`, provide a full strategic campaign plan and note the handoff to the Creative Agent.

**Example when incomplete:**


{
  "agent_response": "To build your social media campaign plan, I need a bit more information: 1. What are your main objectives? 2. Who is your target audience? 3. What is your budget range and timeline?",
  "final_plan": false
}


**Example when complete:**


{
  "agent_response": "Based on the details provided, here’s your complete social media campaign strategy using image and video content. [Insert detailed plan]. Handing off to Creative Agent.",
  "final_plan": true
}

""",
        ),
        id="campaign_planner_agent",
    )

    creative_agent = AgentExecutor(
        agent=chat_client.create_agent(
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
        agent=chat_client.create_agent(
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
        agent=chat_client.create_agent(
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


    hitl_review = RequestInfoExecutor(id="hitl_review")
    final_hitl_approval = RequestInfoExecutor(id="final_hitl_approval")
    coordinator = Coordinator(
        id="coordinator",
        planner_id=campaign_planner_agent.id,
        creative_id=creative_agent.id,
        hitl_review_id=hitl_review.id,
        localization_id=localization_agent.id,
        publishing_id=publishing_agent.id,
        final_hitl_approval_id=final_hitl_approval.id,
    )

    # Build the workflow with name and description for DevUI
    workflow: Workflow = (
        WorkflowBuilder(
            name="Marketing Campaign with Creative Tools and HITL",
            description="Campaign planner → creative agent (images/video) → human review → market selection → localization → publishing schedule → human approval. Multi-stage HITL workflow."
        )
        .set_start_executor(campaign_planner_agent)
        .add_edge(campaign_planner_agent, coordinator)
        .add_edge(coordinator, creative_agent)
        .add_edge(creative_agent, coordinator)
        .add_edge(coordinator, hitl_review)
        .add_edge(hitl_review, coordinator)
        .add_edge(coordinator, localization_agent)
        .add_edge(localization_agent, coordinator)
        .add_edge(coordinator, publishing_agent)
        .add_edge(publishing_agent, coordinator)
        .add_edge(coordinator, final_hitl_approval)
        .add_edge(final_hitl_approval, coordinator)
        .build()
    )
    
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
        requests: list[tuple[str, DraftFeedbackRequest]] = []

        # Process events from the stream
        async for event in stream:
            # Capture human feedback requests
            if isinstance(event, RequestInfoEvent) and isinstance(event.data, DraftFeedbackRequest):
                requests.append((event.request_id, event.data))
            # Capture workflow output
            elif isinstance(event, WorkflowOutputEvent):
                print(f"\n===== Final Result =====\n{event.data}\n")
                completed = True

        # If we have requests, prompt the user
        if requests and not completed:
            responses: dict[str, str] = {}
            for request_id, request in requests:
                print(f"\n----- Social Media Creatives -----")
                print(request.draft_text.strip())
                print(f"\n{request.prompt}")
                answer = input("Your feedback: ").strip()  # noqa: ASYNC250
                if answer.lower() == "exit":
                    print("Exiting...")
                    return
                responses[request_id] = answer
            pending_responses = responses

    print("Workflow complete!")


if __name__ == "__main__":
    asyncio.run(main())

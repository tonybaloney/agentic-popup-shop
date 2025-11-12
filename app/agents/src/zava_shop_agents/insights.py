# Copyright (c) Microsoft. All rights reserved.

import logging
import os
from datetime import datetime
from typing import List, Optional, Union

import httpx
from pydantic import BaseModel, Field
from agent_framework import (
    ChatAgent,
    ChatMessage,
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    WorkflowEvent,
    handler,
    HostedWebSearchTool,
)
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.observability import setup_observability
from agent_framework_azure_ai import AzureAIAgentClient
from azure.identity.aio import DefaultAzureCredential
from zava_shop_agents import MCPStreamableHTTPToolOTEL


logger = logging.getLogger(__name__)


class WeatherAnalysisEvent(WorkflowEvent):
    """Event emitted when weather analysis is complete."""

    def __init__(self, weather_data: "WeatherAnalysis"):
        super().__init__(
            f"Weather analysis complete for {weather_data.city}, {weather_data.state}"
        )
        self.weather_data = weather_data


class EventsAnalysisEvent(WorkflowEvent):
    """Event emitted when events analysis is complete."""

    def __init__(self, event_data: "EventsAnalysis"):
        super().__init__(
            f"Events analysis complete for {event_data.city}, {event_data.state}"
        )
        self.event_data = event_data


class ProductAnalysisEvent(WorkflowEvent):
    """Event emitted when product analysis is complete."""

    def __init__(self, product_data: "ProductsAnalysis"):
        super().__init__(
            f"Product analysis complete for store {product_data.store_id}"
        )
        self.product_data = product_data


class InsightsSynthesizedEvent(WorkflowEvent):
    """Event emitted when final insights are synthesized."""

    def __init__(self, insights: "WeeklyInsights"):
        super().__init__("Weekly insights generated successfully")
        self.insights = insights


WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_API_TIMEOUT = 10.0
DEFAULT_AZURE_API_VERSION = "2024-02-15-preview"

chat_client = AzureOpenAIChatClient(
    api_key=os.environ.get("AZURE_OPENAI_API_KEY_GPT5"),
    endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT_GPT5"),
    deployment_name=os.environ.get("AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5"),
    api_version=os.environ.get(
        "AZURE_OPENAI_ENDPOINT_VERSION_GPT5", DEFAULT_AZURE_API_VERSION
    ),
)

azure_ai_client = AzureAIAgentClient(
    async_credential=DefaultAzureCredential(
        exclude_shared_token_cache_credential=True,
        exclude_visual_studio_code_credential=True,
    ),
    project_endpoint=os.environ.get("AZURE_AI_PROJECT_ENDPOINT"),
    model_deployment_name=os.environ.get(
        "AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4.1-mini"
    ),
)

# Finance MCP Server tool
finance_mcp = MCPStreamableHTTPToolOTEL(
    name="FinanceMCP",
    url=os.getenv("FINANCE_MCP_HTTP", "http://localhost:8002") + "/mcp",
    headers={
        "Authorization": f"Bearer {os.getenv('DEV_GUEST_TOKEN', 'dev-guest-token')}"
    },
    load_tools=True,
    load_prompts=False,
    request_timeout=30,
)

STORE_COORDINATES = {
    1: {"lat": 40.7580, "lon": -73.9855, "city": "New York", "state": "NY"},
    2: {
        "lat": 37.7749,
        "lon": -122.4194,
        "city": "San Francisco",
        "state": "CA",
    },
    3: {"lat": 30.2672, "lon": -97.7431, "city": "Austin", "state": "TX"},
    4: {"lat": 39.7392, "lon": -104.9903, "city": "Denver", "state": "CO"},
    5: {"lat": 41.8781, "lon": -87.6298, "city": "Chicago", "state": "IL"},
    6: {"lat": 42.3601, "lon": -71.0589, "city": "Boston", "state": "MA"},
    7: {"lat": 47.6062, "lon": -122.3321, "city": "Seattle", "state": "WA"},
    8: {"lat": 33.7490, "lon": -84.3880, "city": "Atlanta", "state": "GA"},
    9: {"lat": 25.7617, "lon": -80.1918, "city": "Miami", "state": "FL"},
    10: {"lat": 45.5152, "lon": -122.6784, "city": "Portland", "state": "OR"},
    11: {"lat": 36.1627, "lon": -86.7816, "city": "Nashville", "state": "TN"},
    12: {"lat": 33.4484, "lon": -112.0740, "city": "Phoenix", "state": "AZ"},
    13: {
        "lat": 44.9778,
        "lon": -93.2650,
        "city": "Minneapolis",
        "state": "MN",
    },
    14: {"lat": 35.7796, "lon": -78.6382, "city": "Raleigh", "state": "NC"},
    15: {
        "lat": 40.7608,
        "lon": -111.8910,
        "city": "Salt Lake City",
        "state": "UT",
    },
    16: {
        "lat": 40.7128,
        "lon": -74.0060,
        "city": "Online",
        "state": "N/A",
    },
}


class StoreContext(BaseModel):
    """Store information used to initialize the insights workflow.

    Contains geographic coordinates for weather lookups and identification
    details for filtering product/sales data. Created by DataCollector
    and sent to all three parallel analyzers (weather, events, products).
    """

    store_id: int
    store_name: str
    user_role: str
    latitude: float
    longitude: float
    city: str
    state: str


class InsightAction(BaseModel):
    """Defines a clickable action button displayed on insight cards in the UI.

    Used to navigate users to the AI agent interface with pre-loaded context
    from the insights (weather, events, products). The 'instructions' field
    populates the agent's chat with relevant background information.
    """

    label: str = Field(..., description="Button label text")
    type: str = Field(
        ...,
        description="Action type: 'navigation'",
    )
    path: str = Field(..., description="Navigation path")
    instructions: Optional[str] = Field(
        default=None,
        description="Instructions to pre-fill in the AI agent interface",
    )


class Insight(BaseModel):
    """Represents a single insight card displayed in the management dashboard.

    Each analyzer (weather, events, products) generates one Insight that's
    shown to store managers. Contains a title, description, visual type
    (success/warning/info), and optional action button.
    """

    type: str = Field(
        ..., description="Insight type: 'success', 'warning', or 'info'"
    )
    title: str = Field(..., description="Insight title/heading")
    description: str = Field(..., description="Detailed insight description")
    action: Optional[InsightAction] = Field(
        None, description="Optional action button"
    )


class WeatherAgentResponse(BaseModel):
    """Structured output schema for the weather analysis LLM agent.

    Forces the agent to return a concise, actionable recommendation about
    which apparel categories to stock based on the 7-day forecast.
    """

    analysis: str = Field(
        ...,
        description=(
            "Single actionable sentence (under 40 words): "
            "'Over the next 7 days, expect <concise weather trend>. "
            "Increase stock on <2-3 apparel categories> because "
            "<why they match the forecast>.' "
            "Focus on actionable guidance without extra commentary."
        ),
    )


class WeatherAnalysis(BaseModel):
    """Output from WeatherAnalyzer sent to InsightSynthesizer.

    Contains both the raw weather analysis text and a UI-ready Insight
    object. Sent via workflow context message passing to the synthesizer
    for aggregation with events and products data.
    """

    city: str
    state: str
    store_id: int
    analysis: str
    insight: Insight = Field(
        ..., description="UI-ready insight for weather forecast"
    )


class EventDetail(BaseModel):
    """Represents a single upcoming event that could impact sales.

    Part of structured output from EventsSearchAgent (Bing search).
    Contains event details and retail relevance explanation.
    """

    event_name: str = Field(..., description="Name of the upcoming event")
    event_date: str = Field(
        ..., description="Exact date of the event (e.g., 'November 27, 2025')"
    )
    location: str = Field(..., description="Specific location or venue")
    expected_attendance: str = Field(
        ...,
        description="Expected crowd size (e.g., '~50,000 people', '3 million spectators')",
    )
    relevance: str = Field(
        ...,
        description="Why this event is relevant for retail - brief explanation",
    )
    product_categories: List[str] = Field(
        default_factory=list,
        description="Product categories that would be in high demand (e.g., 'Athletic Wear', 'Outerwear', 'Accessories')",
    )


class EventsAgentResponse(BaseModel):
    """Structured output schema for EventsSearchAgent LLM (Azure AI + Bing).

    Forces the agent to return events in a consistent format with summary.
    Used as response_format parameter in agent.run() call.
    """

    events: List[EventDetail] = Field(
        default_factory=list,
        description="List of 1-3 major upcoming events in the next 21 days with expected attendance over 5000 people",
    )
    summary: str = Field(
        ...,
        description=(
            "Brief 1-2 sentence summary of the events landscape. "
            "If no major events found, state: "
            "'No major upcoming events expected in the next 21 days.'"
        ),
    )


class EventsAnalysis(BaseModel):
    """Output from EventsAnalyzer sent to InsightSynthesizer.

    Contains structured list of events found via Bing search, summary text,
    and UI-ready Insight object. Sent via workflow context to synthesizer
    for aggregation with weather and products data.
    """

    city: str
    state: str
    events: List[EventDetail] = Field(
        default_factory=list, description="List of relevant upcoming events"
    )
    summary: str = Field(
        ..., description="Overall summary of events happening in the area"
    )
    insight: Insight = Field(
        ..., description="UI-ready insight for local events"
    )


class ProductsAnalysis(BaseModel):
    """Output from TopSellingProductsAnalyzer sent to InsightSynthesizer.

    Contains top 5 products retrieved via Finance MCP server tools, formatted
    as display strings. Sent via workflow context to synthesizer for
    aggregation with weather and events data.
    """

    city: str
    state: str
    store_id: int
    analysis_text: str = Field(
        ...,
        description="Formatted analysis from MCP tools including inventory levels and sales performance",
    )
    low_stock_items: List[str] = Field(
        default_factory=list,
        description="List of low stock items with quantities",
    )
    top_products: List[str] = Field(
        default_factory=list,
        description="List of top performing products with order counts",
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Stock recommendations based on data"
    )
    insight: Insight = Field(
        ..., description="UI-ready insight for product performance"
    )


class ProductDetail(BaseModel):
    """Represents sales data for a single product over a time period.

    Returned by Finance MCP server tools. Contains product identification
    (name, SKU, category) and performance metrics (units sold, revenue).
    """

    product_name: str = Field(..., description="Name of the product")
    sku: Optional[str] = Field(
        None, description="SKU identifier when available"
    )
    category_name: Optional[str] = Field(
        None, description="Category label if provided"
    )
    units_sold: int = Field(..., description="Total units sold in the period")
    revenue: float = Field(..., description="Total revenue generated in USD")
    avg_price: Optional[float] = Field(
        None, description="Average unit price if returned by the tool"
    )


class ProductsAgentResponse(BaseModel):
    """Structured output schema for Top Selling Products Analyzer agent.

    Forces the agent to return product data in consistent format after
    calling Finance MCP tools. Used as response_format in agent.run().
    """

    products: List[ProductDetail] = Field(
        default_factory=list,
        description=(
            "Top 5 selling products from the last 21 days, ordered by "
            "units sold descending. Each product must include product_name, "
            "units_sold, revenue, and optionally sku."
        ),
    )


class WeeklyInsights(BaseModel):
    """Final workflow output returned to the management dashboard UI.

    Aggregates all three insights (weather, events, products) plus a
    unified action button that navigates to AI agent with full context.
    Created by InsightSynthesizer after fan-in from all analyzers.
    """

    summary: str = Field(
        ..., description="AI-generated insights disclaimer (shown in italics)"
    )
    weather_summary: str = Field(
        ..., description="Summary of weather conditions"
    )
    events_summary: Optional[str] = Field(
        None, description="Summary of local events"
    )
    stock_items: List[str] = Field(
        default_factory=list,
        description="List of specific product items to stock up on (determined by stock agent)",
    )
    insights: List[Insight] = Field(
        ..., description="List of specific insights"
    )
    unified_action: Optional[InsightAction] = Field(
        None,
        description="Single unified action that combines all insights for stock agent analysis",
    )


class DataCollector(Executor):
    """Collects store context and sends to all parallel analyzers (fan-out).

    Parses incoming ChatMessage to extract store details, enriches with
    geographic coordinates from STORE_COORDINATES lookup, and broadcasts
    StoreContext to weather, events, and products analyzers.
    """

    def __init__(self, id: str | None = None):
        super().__init__(id=id or "data_collector")

    @handler
    async def handle(
        self, message: ChatMessage, ctx: WorkflowContext[StoreContext]
    ) -> None:
        """Extract store context from input message and broadcast to analyzers.

        Parses comma-separated key:value format, looks up coordinates,
        and creates StoreContext for downstream processing.

        Expected input format: "store_id:X,user_role:Y,store_name:Z"
        Example: "store_id:1,user_role:manager,store_name:Downtown Seattle"

        Args:
            message: ChatMessage containing store details
            ctx: Workflow context for broadcasting StoreContext

        Raises:
            ValueError: If message format is invalid or store_id cannot be parsed
        """
        try:
            # Parse key:value pairs from comma-separated input
            parts = message.text.split(",")
            store_id = int(parts[0].split(":")[1].strip())
            user_role = parts[1].split(":")[1].strip()
            store_name = parts[2].split(":")[1].strip()

            # Lookup coordinates, default to NYC (store 1) if not found
            coords = STORE_COORDINATES.get(store_id, STORE_COORDINATES[1])

            store_context = StoreContext(
                store_id=store_id,
                store_name=store_name,
                user_role=user_role,
                latitude=coords["lat"],
                longitude=coords["lon"],
                city=coords["city"],
                state=coords["state"],
            )

            await ctx.send_message(store_context)

        except (IndexError, ValueError, KeyError) as e:
            logger.error(
                "Failed to parse store context: %s", str(e), exc_info=True
            )
            raise ValueError(
                f"Failed to parse store context. Expected format: 'store_id:X,user_role:Y,store_name:Z'. "
                f"Got: {message.text}"
            ) from e


class WeatherAnalyzer(Executor):
    """Fetches weather forecasts and generates apparel stocking recommendations.

    Calls Open-Meteo API for 7-day forecast, then uses LLM to translate
    weather patterns into actionable retail guidance. Outputs WeatherAnalysis
    with both raw text and UI-ready Insight for the synthesizer.
    """

    def __init__(self, id: str | None = None):
        super().__init__(id=id or "weather_analyzer")
        self._weather_agent = chat_client.create_agent(
            instructions=(
                "You analyze the next 7 days of weather to guide apparel stocking. "
                "Respond in a single sentence using this structure: "
                "'Over the next 7 days, expect <concise weather trend>. "
                "Increase stock on <2-3 apparel categories> because <why they match the forecast>.' "
                "Keep it under 40 words, avoid extra commentary, and focus on actionable guidance."
            ),
            response_format=WeatherAgentResponse,
        )

    @handler
    async def handle(
        self, context: StoreContext, ctx: WorkflowContext[WeatherAnalysis]
    ) -> None:
        """Fetch weather data from Open-Meteo API and use LLM to generate insights."""
        try:
            params = {
                "latitude": context.latitude,
                "longitude": context.longitude,
                "current": (
                    "temperature_2m,weather_code,relative_humidity_2m,"
                    "wind_speed_10m"
                ),
                "daily": (
                    "temperature_2m_max,temperature_2m_min,precipitation_sum,"
                    "precipitation_probability_max,weather_code,"
                    "wind_speed_10m_max,uv_index_max"
                ),
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "precipitation_unit": "inch",
                "timezone": "auto",
                "forecast_days": 7,
            }

            async with httpx.AsyncClient(
                timeout=WEATHER_API_TIMEOUT
            ) as client:
                response = await client.get(WEATHER_API_URL, params=params)
                response.raise_for_status()
                weather_api_data = response.json()

            weather_prompt = (
                "Analyze this 7-day weather forecast for "
                f"{context.city}, {context.state} and recommend specific clothing/apparel "
                "inventory categories to stock:"
                f" {weather_api_data}"
            )

            llm_response = await self._weather_agent.run(weather_prompt)
            weather_payload = getattr(llm_response, "value", None)

            if weather_payload and getattr(weather_payload, "analysis", None):
                weather_text = weather_payload.analysis
            else:
                fallback_text = (llm_response.text or "").strip()
                if fallback_text:
                    weather_text = fallback_text
                else:
                    logger.warning(
                        "Weather agent returned no structured payload or text for store_id=%s",
                        context.store_id,
                    )
                    raise ValueError("Weather agent returned empty analysis")

            # Create insight for UI
            weather_ui_insight = Insight(
                type="info",
                title="🌦️ Weather Forecast",
                description=f"{weather_text}",
                action=None,
            )

            weather_data = WeatherAnalysis(
                city=context.city,
                state=context.state,
                store_id=context.store_id,
                analysis=weather_text,
                insight=weather_ui_insight,
            )

            weather_event = WeatherAnalysisEvent(weather_data)
            weather_event.executor_id = self.id
            await ctx.add_event(weather_event)
            await ctx.send_message(weather_data)
        except (
            httpx.HTTPError,
            httpx.TimeoutException,
            KeyError,
            ValueError,
        ) as e:
            logger.error(
                "Weather service call failed for store_id=%s (%s, %s): %s",
                context.store_id,
                context.city,
                context.state,
                str(e),
                exc_info=True,
            )

            # Create fallback insight for UI
            fallback_insight = Insight(
                type="warning",
                title="🌦️ Weather Forecast",
                description="⚠️ Weather data unavailable - check alternative sources for forecast information.",
                action=None,
            )

            weather_data = WeatherAnalysis(
                city=context.city,
                state=context.state,
                store_id=context.store_id,
                analysis="Weather data unavailable at this time.",
                insight=fallback_insight,
            )

            weather_event = WeatherAnalysisEvent(weather_data)
            weather_event.executor_id = self.id
            await ctx.add_event(weather_event)
            await ctx.send_message(weather_data)


class EventsAnalyzer(Executor):
    """Uses Bing search to find local events and generate insights."""

    def __init__(self, id: str | None = None):
        super().__init__(id=id or "events_analyzer")
        self._events_agent = azure_ai_client.create_agent(
            name="EventsSearchAgent",
            instructions=(
                "You are helping a retail clothing store manager identify upcoming events that could increase apparel sales. "
                "Search for major public events in the next 21 days (parades, marathons, outdoor festivals, "
                "sporting events, concerts with 5,000+ attendees). "
                "For each event found, provide: "
                "1) Event name and date, "
                "2) Why it's relevant for clothing/apparel sales (e.g., 'Outdoor parade - expect demand "
                "for warm jackets, scarves, hats'). "
                "Focus ONLY on events that would drive foot traffic and clothing purchases. "
                "Exclude indoor entertainment and avoid citations. "
                "Keep responses concise (2-4 sentences). If no relevant events found, say: " \
                "'No major upcoming events expected in the next 21 days.' "
                "Always return your answer as JSON that matches the provided response schema."
            ),
            tools=[HostedWebSearchTool(description="Search for local events")],
        )

    @handler
    async def handle(
        self, context: StoreContext, ctx: WorkflowContext[EventsAnalysis]
    ) -> None:
        """Search for local events using Azure AI Agent with Bing Custom Search."""
        try:
            if not os.environ.get(
                "BING_CUSTOM_CONNECTION_ID"
            ) or not os.environ.get("BING_CUSTOM_INSTANCE_NAME"):
                raise ValueError(
                    "Bing Custom Search not configured. Required environment variables: "
                    "BING_CUSTOM_CONNECTION_ID, BING_CUSTOM_INSTANCE_NAME"
                )

            today = datetime.now().strftime("%B %d, %Y")
            response = await self._events_agent.run(
                f"Major outdoor public events after {today} in {context.city}, "
                f"{context.state} that would increase clothing store sales",
                response_format=EventsAgentResponse,
            )

            # Structured output guarantees schema compliance
            events_payload = response.value
            structured_events = (
                [EventDetail.model_validate(event) for event in events_payload.events]
                if events_payload and events_payload.events
                else []
            )
            events_summary = (
                events_payload.summary
                if events_payload and events_payload.summary
                else "No major upcoming events expected in the next 21 days."
            )

            has_events = bool(structured_events) or (
                "no major" not in events_summary.lower()
            )

            if has_events:
                events_ui_insight = Insight(
                    type="info",
                    title="🎉 Local Events",
                    description=f"📅 {events_summary}",
                    action=None,
                )
            else:
                events_ui_insight = Insight(
                    type="info",
                    title="🎉 Local Events",
                    description="ℹ️ No major upcoming events expected in the next 21 days.",
                    action=None,
                )

            event_data = EventsAnalysis(
                city=context.city,
                state=context.state,
                events=structured_events,
                summary=events_summary
                if has_events
                else "No major upcoming events expected in the next 21 days.",
                insight=events_ui_insight,
            )

            events_event = EventsAnalysisEvent(event_data)
            events_event.executor_id = self.id
            await ctx.add_event(events_event)
            await ctx.send_message(event_data)

        except Exception as e:
            logger.error(
                "Events analysis failed for store_id=%s: %s",
                context.store_id,
                str(e),
                exc_info=True,
            )
            # Create fallback insight for UI
            fallback_insight = Insight(
                type="warning",
                title="🎉 Local Events",
                description="⚠️ Unable to retrieve local events at this time.",
                action=None,
            )

            event_data = EventsAnalysis(
                city=context.city,
                state=context.state,
                events=[],
                summary="Unable to retrieve local events at this time",
                insight=fallback_insight,
            )

            events_event = EventsAnalysisEvent(event_data)
            events_event.executor_id = self.id
            await ctx.add_event(events_event)
            await ctx.send_message(event_data)


class TopSellingProductsAnalyzer(Executor):
    """Analyzes top selling products using Finance MCP tools."""

    agent: ChatAgent

    def __init__(self, id: str | None = None):
        # Create an agent with Finance MCP tools
        self.agent = chat_client.create_agent(
            name="Top Selling Products Analyzer",
            instructions=(
                "You are a retail analyst analyzing product performance. "
                "Your task: retrieve the top 5 selling products for a specific store over the last 21 days. "
                "Use the finance MCP tools to get revenue, units sold, and SKU for each product. "
                "Limit results to exactly 5 products and order by units sold in descending order. "
                "Always respond using the provided response schema."
            ),
            tools=[finance_mcp],
        )
        super().__init__(id=id or "top_selling_products_analyzer")

    @handler
    async def handle(
        self, context: StoreContext, ctx: WorkflowContext[ProductsAnalysis]
    ) -> None:
        """Fetch top selling products from Finance MCP."""
        try:
            agent_response = await self.agent.run(
                f"Top 5 selling products for store_id {context.store_id} over the last 21 days. "
                f"Use the finance MCP tools to retrieve revenue, units sold, and SKU."
                f" Limit results to 5 and order by units sold descending.",
                response_format=ProductsAgentResponse,
            )

            products_payload = agent_response.value
            products = (products_payload.products if products_payload else [])[
                :5
            ]

            if not products:
                formatted_summary = (
                    "No product data returned for the last 21 days."
                )
                product_strings: List[str] = []
            else:
                lines: List[str] = []
                product_strings = []
                for index, product in enumerate(products, start=1):
                    revenue = product.revenue
                    units = product.units_sold

                    line_parts = [
                        f"{index}. {product.product_name}",
                        f"Units sold: {units}",
                        f"Revenue: ${revenue:,.2f}",
                    ]
                    if product.sku:
                        line_parts.append(f"SKU: {product.sku}")

                    formatted_line = " - ".join(line_parts)
                    lines.append(formatted_line)
                    product_strings.append(formatted_line)

                formatted_summary = "\n".join(lines)

            product_ui_insight = Insight(
                type="success",
                title="📈 Top Selling Products (Last 21 Days)",
                description=f"📊 {formatted_summary}",
                action=None,
            )

            product_data = ProductsAnalysis(
                city=context.city,
                state=context.state,
                store_id=context.store_id,
                analysis_text=formatted_summary,
                low_stock_items=[],
                top_products=product_strings,
                recommendations=[],
                insight=product_ui_insight,
            )

            product_event = ProductAnalysisEvent(product_data)
            product_event.executor_id = self.id
            await ctx.add_event(product_event)
            await ctx.send_message(product_data)

        except Exception as e:
            logger.error(
                "Product analysis failed for store_id=%s: %s",
                context.store_id,
                str(e),
                exc_info=True,
            )
            # Create fallback insight for UI
            fallback_insight = Insight(
                type="warning",
                title="📈 Top Selling Products (Last 21 Days)",
                description="⚠️ Unable to retrieve product data at this time. Check inventory system availability.",
                action=None,
            )

            product_data = ProductsAnalysis(
                city=context.city,
                state=context.state,
                store_id=context.store_id,
                analysis_text="Unable to retrieve product data at this time",
                low_stock_items=[],
                top_products=[],
                recommendations=["Check inventory system availability"],
                insight=fallback_insight,
            )

            product_event = ProductAnalysisEvent(product_data)
            product_event.executor_id = self.id
            await ctx.add_event(product_event)
            await ctx.send_message(product_data)


class InsightSynthesizer(Executor):
    """Aggregates weather, product, and events data to generate final insights (fan-in)."""

    def __init__(self, id: str | None = None):
        super().__init__(id=id or "insight_synthesizer")

    @handler
    async def handle(
        self,
        data: List[Union[WeatherAnalysis, EventsAnalysis, ProductsAnalysis]],
        ctx: WorkflowContext[WeeklyInsights],
    ) -> None:
        """Collect aggregated data from fan-in and synthesize insights."""
        weather_data: Optional[WeatherAnalysis] = None
        event_data: Optional[EventsAnalysis] = None
        product_data: Optional[ProductsAnalysis] = None

        for item in data:
            if isinstance(item, WeatherAnalysis):
                weather_data = item
            elif isinstance(item, EventsAnalysis):
                event_data = item
            elif isinstance(item, ProductsAnalysis):
                product_data = item

        await self._try_synthesize(weather_data, event_data, product_data, ctx)

    async def _try_synthesize(
        self,
        weather_data: Optional[WeatherAnalysis],
        event_data: Optional[EventsAnalysis],
        product_data: Optional[ProductsAnalysis],
        ctx: WorkflowContext[WeeklyInsights],
    ) -> None:
        """Generate final insights when all data is available."""
        if weather_data is None or event_data is None or product_data is None:
            logger.warning(
                "Missing data - weather: %s, events: %s, products: %s",
                weather_data is not None,
                event_data is not None,
                product_data is not None,
            )
            return

        # Build unified action with comprehensive instructions for AI stock agent
        events_context = (
            f"### Upcoming Events\n{event_data.summary}\n\n"
            if event_data.summary
            and "no major" not in event_data.summary.lower()
            else ""
        )

        top_products_context = (
            f"### Top Selling Products\n{product_data.analysis_text}\n\n"
        )

        unified_instructions = (
            f"Based on the weather conditions, local events, and current sales performance, what items should we restock?\n\n"
            f"## CONTEXT\n\n"
            f"Weather Forecast:\n"
            f"- {weather_data.analysis}\n\n"
            f"{events_context}"
            f"{top_products_context}"
        )

        unified_action = InsightAction(
            label="Generate Insights-Based Analysis",
            type="navigation",
            path="/management/ai-agent",
            instructions=unified_instructions,
        )

        # Collect insights from all analyzers
        insights_list = [
            weather_data.insight,
            product_data.insight,
            event_data.insight,
        ]

        insights = WeeklyInsights(
            unified_action=unified_action,
            summary="AI-generated insights based on weather forecasts, inventory data, and local events",
            weather_summary=weather_data.analysis,
            events_summary=event_data.summary
            if "no major" not in event_data.summary.lower()
            else None,
            stock_items=[],
            insights=insights_list,
        )

        synth_event = InsightsSynthesizedEvent(insights)
        synth_event.executor_id = self.id
        await ctx.add_event(synth_event)
        await ctx.send_message(insights)
        await ctx.yield_output(insights)


def get_workflow():
    """Create and return the weekly insights workflow.

    Fan-out/fan-in pattern: collects store context, analyzes weather/events/products
    in parallel, then synthesizes actionable retail insights.

    Returns:
        Workflow: Configured workflow ready for execution
    """
    data_collector = DataCollector(id="data_collector")
    weather_analyzer = WeatherAnalyzer(id="weather_analyzer")
    events_analyzer = EventsAnalyzer(id="events_analyzer")
    top_selling_products_analyzer = TopSellingProductsAnalyzer(
        id="top_selling_products_analyzer"
    )
    insight_synthesizer = InsightSynthesizer(id="insight_synthesizer")

    workflow = (
        WorkflowBuilder(
            name="Weekly Insights Workflow",
            description="Generates actionable retail insights by analyzing weather patterns, "
            "local events, and top selling products. Uses parallel data gathering (fan-out) and "
            "intelligent synthesis (fan-in) to provide store managers with "
            "context-aware stocking recommendations.",
        )
        .set_start_executor(data_collector)
        .add_fan_out_edges(
            data_collector,
            [weather_analyzer, events_analyzer, top_selling_products_analyzer],
        )
        .add_fan_in_edges(
            [weather_analyzer, events_analyzer, top_selling_products_analyzer],
            insight_synthesizer,
        )
        .build()
    )

    return workflow


workflow = get_workflow()

setup_observability()

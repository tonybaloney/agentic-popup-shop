# Copyright (c) Microsoft. All rights reserved.

import json
import logging
import os
from typing import List, Optional, Any

from pydantic import BaseModel, Field
from agent_framework import (
    ChatAgent,
    ChatMessage,
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    WorkflowEvent,
    handler,
)
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.observability import setup_observability
from zava_shop_agents import MCPStreamableHTTPToolOTEL


logger = logging.getLogger(__name__)


class StorePerformanceEvent(WorkflowEvent):
    """Event emitted when store performance analysis is complete."""

    def __init__(self, performance_data: "StorePerformanceAnalysis"):
        super().__init__(
            f"Store performance analysis complete - {len(performance_data.stores)} stores analyzed"
        )
        self.performance_data = performance_data


class AdminInsightsSynthesizedEvent(WorkflowEvent):
    """Event emitted when final admin insights are synthesized."""

    def __init__(self, insights: "AdminWeeklyInsights"):
        super().__init__("Admin weekly insights generated successfully")
        self.insights = insights


DEFAULT_AZURE_API_VERSION = "2024-02-15-preview"

chat_client = AzureOpenAIChatClient(
    api_key=os.environ.get("AZURE_OPENAI_API_KEY_GPT5"),
    endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT_GPT5"),
    deployment_name=os.environ.get("AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5"),
    api_version=os.environ.get(
        "AZURE_OPENAI_ENDPOINT_VERSION_GPT5", DEFAULT_AZURE_API_VERSION
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


class AdminContext(BaseModel):
    """Admin user context for enterprise-wide insights.

    Contains user role verification for admin-level access.
    Unlike store manager workflows, no store_id filtering is needed
    since admins see all stores.
    """

    user_role: str
    days_back: int = Field(
        default=30, description="Number of days to analyze (default: 30)"
    )


class InsightAction(BaseModel):
    """Defines a clickable action button displayed on insight cards in the UI."""

    label: str = Field(..., description="Button label text")
    type: str = Field(..., description="Action type: 'navigation'")
    path: str = Field(..., description="Navigation path")
    instructions: Optional[str] = Field(
        default=None,
        description="Instructions to pre-fill in the AI agent interface",
    )


class Insight(BaseModel):
    """Represents a single insight card displayed in the admin dashboard."""

    type: str = Field(
        ..., description="Insight type: 'success', 'warning', or 'info'"
    )
    title: str = Field(..., description="Insight title/heading")
    description: str = Field(..., description="Detailed insight description")
    action: Optional[InsightAction] = Field(
        None, description="Optional action button"
    )


class StorePerformanceMetric(BaseModel):
    """Performance metrics for a single store."""

    store_id: int
    store_name: str
    is_online: bool
    total_revenue: float
    total_orders: int
    total_units_sold: int
    unique_customers: int
    avg_order_value: float
    revenue_per_customer: float
    efficiency_rank: int


class StorePerformanceAnalysis(BaseModel):
    """Output from StorePerformanceAnalyzer sent to InsightSynthesizer.

    Contains comprehensive performance data for all stores ranked by
    revenue-per-customer efficiency metric.
    """

    days_back: int
    stores: List[StorePerformanceMetric] = Field(
        default_factory=list, description="All stores ranked by efficiency"
    )
    top_performers: List[str] = Field(
        default_factory=list,
        description="Top 3 most efficient stores (formatted strings)",
    )
    bottom_performers: List[str] = Field(
        default_factory=list,
        description="Bottom 3 stores needing improvement (formatted strings)",
    )
    total_revenue: float = Field(
        ..., description="Total revenue across all stores"
    )
    total_customers: int = Field(
        ..., description="Total unique customers across all stores"
    )
    analysis_summary: str = Field(
        ..., description="AI-generated summary of performance patterns"
    )
    insight: Insight = Field(
        ..., description="UI-ready insight for store performance"
    )


class AdminWeeklyInsights(BaseModel):
    """Final workflow output returned to the admin dashboard UI.

    Provides enterprise-wide insights focused on comparative store
    performance, efficiency metrics, and strategic recommendations.
    
    Note: Inherits WeeklyInsights schema for API compatibility.
    Admin workflow doesn't use weather/events, so those fields are None.
    """

    store_id: int = Field(
        default=0, description="Store ID (0 for admin enterprise-wide insights)"
    )
    summary: str = Field(
        ..., description="AI-generated insights disclaimer (shown in italics)"
    )
    weather_summary: str = Field(
        default="N/A - Admin enterprise view",
        description="Not used in admin workflow"
    )
    events_summary: Optional[str] = Field(
        default=None,
        description="Not used in admin workflow"
    )
    stock_items: List[str] = Field(
        default_factory=list,
        description="Not used in admin workflow"
    )
    insights: List[Insight] = Field(..., description="List of specific insights")
    unified_action: Optional[InsightAction] = Field(
        None,
        description="Single unified action for deep-dive analysis",
    )


class AdminContextCollector(Executor):
    """Collects admin context and initiates performance analysis."""

    def __init__(self, id: str | None = None):
        super().__init__(id=id or "admin_context_collector")

    @handler
    async def handle(
        self, message: ChatMessage, ctx: WorkflowContext[AdminContext]
    ) -> None:
        """Extract admin context from input message.

        Args:
            message: ChatMessage containing user role and optional days_back in format:
                    "Generate admin weekly insights:\nUser Role: admin\nDays Back: 30"
            ctx: Workflow context for broadcasting AdminContext

        Raises:
            ValueError: If user is not an admin
        """
        import re
        
        text = message.text.strip()
        user_role = None
        days_back = 30  # Default value

        try:
            # Extract user_role using regex
            # Pattern: "User Role: admin" (case-insensitive)
            role_match = re.search(r'user[_ ]role\s*:\s*([a-z_]+)', text, re.IGNORECASE)
            if role_match:
                user_role = role_match.group(1)

            # Extract days_back if present
            # Pattern: "Days Back: 30" (case-insensitive)
            days_match = re.search(r'days[_ ]back\s*:\s*(\d+)', text, re.IGNORECASE)
            if days_match:
                days_back = int(days_match.group(1))

            # Validate we got user_role
            if user_role is None:
                raise ValueError(
                    f"Could not parse user_role from message. "
                    f"Expected format: 'User Role: <role>'. "
                    f"Got: {text}"
                )

            # Verify admin role
            if user_role.lower() != "admin":
                raise ValueError(
                    f"Admin insights require admin role. Got: {user_role}"
                )

            admin_context = AdminContext(
                user_role=user_role, days_back=days_back
            )

            await ctx.send_message(admin_context)

        except Exception as e:
            logger.error(
                "Failed to parse admin context: %s", str(e), exc_info=True
            )
            raise ValueError(
                f"Failed to extract admin information from message. "
                f"Expected admin user role. Got: {message.text}"
            ) from e


class StorePerformanceAnalyzer(Executor):
    """Analyzes store performance using Finance MCP get_store_performance_comparison tool."""

    agent: ChatAgent

    def __init__(self, id: str | None = None):
        # Create agent with Finance MCP tools - agent handles connection automatically
        self.agent = chat_client.create_agent(
            name="Store Performance Analyzer",
            instructions=(
                "You are an enterprise retail analyst analyzing store performance across all locations. "
                "Your task: retrieve comprehensive performance metrics for all stores using the "
                "get_store_performance_comparison tool from Finance MCP. "
                "Pass days_back parameter to the tool. "
                "The tool returns stores ranked by revenue per customer (efficiency metric). "
                "Return the raw JSON data from the tool so it can be parsed and analyzed."
            ),
            tools=[finance_mcp],
        )
        super().__init__(id=id or "store_performance_analyzer")

    @handler
    async def handle(
        self,
        context: AdminContext,
        ctx: WorkflowContext[StorePerformanceAnalysis],
    ) -> None:
        """Fetch store performance comparison from Finance MCP via agent and analyze patterns."""
        try:
            # Use agent to call MCP tool - agent manages connection automatically
            prompt = (
                f"Get store performance comparison data for the last {context.days_back} days. "
                f"Use the get_store_performance_comparison tool with days_back={context.days_back}. "
                f"Return the complete results."
            )
            
            # Define response schema for the agent
            class PerformanceToolResponse(BaseModel):
                stores: List[StorePerformanceMetric]
            
            agent_response = await self.agent.run(
                prompt,
                response_format=PerformanceToolResponse
            )
            
            # Extract stores from structured response
            stores = agent_response.value.stores if agent_response.value else []
            
            # If no results from agent, raise error
            if not stores:
                raise ValueError("No store performance data returned from Finance MCP tool")
            
            # Calculate totals
            total_revenue = sum(s.total_revenue for s in stores)
            total_customers = sum(s.unique_customers for s in stores)
            
            # Extract top and bottom performers
            top_3 = stores[:3] if len(stores) >= 3 else stores
            bottom_3 = stores[-3:] if len(stores) >= 3 else []
            
            # Format top performers
            top_performers = [
                f"🥇 #{store.efficiency_rank} {store.store_name}: ${store.revenue_per_customer:,.2f}/customer "
                f"({store.unique_customers} customers, ${store.total_revenue:,.2f} revenue)"
                for store in top_3
            ]
            
            # Format bottom performers
            bottom_performers = [
                f"#{store.efficiency_rank} {store.store_name}: ${store.revenue_per_customer:,.2f}/customer "
                f"({store.unique_customers} customers, ${store.total_revenue:,.2f} revenue)"
                for store in bottom_3
            ]
            
            # Generate analysis summary using separate LLM agent
            analysis_prompt = (
                f"Analyze this store performance data and provide executive insights:\n\n"
                f"Total Stores: {len(stores)}\n"
                f"Total Revenue: ${total_revenue:,.2f}\n"
                f"Total Customers: {total_customers:,}\n"
                f"Average Revenue per Customer: ${total_revenue/total_customers:,.2f}\n\n"
                f"Top 3 Performers (by revenue per customer):\n"
                f"{chr(10).join(top_performers)}\n\n"
                f"Bottom 3 Performers:\n"
                f"{chr(10).join(bottom_performers)}\n\n"
                f"Provide a concise 2-3 sentence analysis highlighting:\n"
                f"1) The efficiency gap between top and bottom performers\n"
                f"2) Key patterns or insights about what makes top stores successful\n"
                f"3) One actionable recommendation for improving bottom performers"
            )
            
            analysis_agent = chat_client.create_agent(
                name="PerformanceAnalyzer",
                instructions="Provide concise executive insights from store performance data."
            )
            analysis_response = await analysis_agent.run(analysis_prompt)
            analysis_text = analysis_response.text or "Performance analysis completed."
            
            # Create detailed description for UI
            description_parts = [
                f"📊 Analyzed {context.days_back}-day performance across {len(stores)} stores.",
                f"💰 Total Revenue: ${total_revenue:,.2f} | 👥 Total Customers: {total_customers:,}",
                "",
                "🏆 Top Performers:",
            ]
            description_parts.extend(f"  {line}" for line in top_performers[:3])
            description_parts.extend(["", "📉 Needs Improvement:"])
            description_parts.extend(f"  {line}" for line in bottom_performers[:3])
            
            # Create insight for UI
            performance_insight = Insight(
                type="info",
                title="🏪 Store Performance Comparison",
                description="\n".join(description_parts),
                action=InsightAction(
                    label="View Detailed Analysis",
                    type="navigation",
                    path="/management/ai-agent",
                    instructions=(
                        f"Analyze store performance trends and provide recommendations:\n\n"
                        f"{analysis_text}\n\n"
                        f"Review all {len(stores)} stores and identify opportunities for improvement."
                    ),
                ),
            )

            performance_data = StorePerformanceAnalysis(
                days_back=context.days_back,
                stores=stores,
                top_performers=top_performers,
                bottom_performers=bottom_performers,
                total_revenue=total_revenue,
                total_customers=total_customers,
                analysis_summary=analysis_text,
                insight=performance_insight,
            )

            performance_event = StorePerformanceEvent(performance_data)
            performance_event.executor_id = self.id
            await ctx.add_event(performance_event)
            await ctx.send_message(performance_data)

        except Exception as e:
            logger.error(
                "Store performance analysis failed: %s",
                str(e),
                exc_info=True,
            )
            # Create fallback insight for UI
            fallback_insight = Insight(
                type="warning",
                title="🏪 Store Performance Comparison",
                description="⚠️ Unable to retrieve store performance data at this time. Check Finance MCP server availability.",
                action=None,
            )

            performance_data = StorePerformanceAnalysis(
                days_back=context.days_back,
                stores=[],
                top_performers=["Unable to retrieve performance data"],
                bottom_performers=[],
                total_revenue=0.0,
                total_customers=0,
                analysis_summary="Unable to retrieve store performance data at this time",
                insight=fallback_insight,
            )

            performance_event = StorePerformanceEvent(performance_data)
            performance_event.executor_id = self.id
            await ctx.add_event(performance_event)
            await ctx.send_message(performance_data)


class AdminInsightSynthesizer(Executor):
    """Synthesizes admin-level insights from store performance analysis."""

    def __init__(self, id: str | None = None):
        super().__init__(id=id or "admin_insight_synthesizer")

    @handler
    async def handle(
        self,
        performance_data: StorePerformanceAnalysis,
        ctx: WorkflowContext[AdminWeeklyInsights],
    ) -> None:
        """Generate final admin insights from performance analysis."""

        # Build unified action with comprehensive instructions
        unified_instructions = (
            f"Based on store performance analysis over the last {performance_data.days_back} days, "
            f"provide strategic recommendations for improving enterprise-wide performance.\n\n"
            f"## PERFORMANCE CONTEXT\n\n"
            f"{performance_data.analysis_summary}\n\n"
            f"### Top Performers\n"
            f"{chr(10).join(performance_data.top_performers)}\n\n"
            f"### Areas for Improvement\n"
            f"{chr(10).join(performance_data.bottom_performers)}\n\n"
        )

        unified_action = InsightAction(
            label="Generate Strategic Analysis",
            type="navigation",
            path="/management/ai-agent",
            instructions=unified_instructions,
        )

        insights = AdminWeeklyInsights(
            store_id=0,  # Cache key for admin enterprise-wide insights
            summary="AI-generated enterprise insights based on comparative store performance and efficiency metrics",
            weather_summary="N/A - Admin enterprise view",  # Required by WeeklyInsights schema
            events_summary=None,
            stock_items=[],
            insights=[performance_data.insight],
            unified_action=unified_action,
        )

        synth_event = AdminInsightsSynthesizedEvent(insights)
        synth_event.executor_id = self.id
        await ctx.add_event(synth_event)
        await ctx.send_message(insights)
        await ctx.yield_output(insights)


def get_admin_workflow():
    """Create and return the admin weekly insights workflow.

    Simpler than store manager workflow - no weather/events needed.
    Focuses on comparative store performance analysis using
    get_store_performance_comparison MCP tool.

    Returns:
        Workflow: Configured admin workflow ready for execution
    """
    context_collector = AdminContextCollector(id="admin_context_collector")
    performance_analyzer = StorePerformanceAnalyzer(
        id="store_performance_analyzer"
    )
    insight_synthesizer = AdminInsightSynthesizer(
        id="admin_insight_synthesizer"
    )

    workflow = (
        WorkflowBuilder(
            name="Admin Weekly Insights Workflow",
            description=(
                "Generates enterprise-wide insights for admin users by analyzing "
                "comparative store performance metrics. Uses Finance MCP's "
                "get_store_performance_comparison tool to rank stores by efficiency "
                "(revenue per customer) and identify top performers and improvement opportunities."
            ),
        )
        .set_start_executor(context_collector)
        .add_edge(context_collector, performance_analyzer)
        .add_edge(performance_analyzer, insight_synthesizer)
        .build()
    )

    return workflow


admin_workflow = get_admin_workflow()

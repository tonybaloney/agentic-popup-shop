# Copyright (c) Microsoft. All rights reserved.
import os
from typing import Any, Sequence, cast

from agent_framework import (
    Agent,
    Message,
    Executor,
    WorkflowBuilder,
    WorkflowContext,
    Workflow,
    handler,
)
from agent_framework_azure_ai import AzureAIClient
from azure.identity.aio import DefaultAzureCredential
from azure.core.credentials_async import AsyncTokenCredential

from zava_shop_agents import MCPStreamableHTTPToolOTEL, StrictModel


WORKFLOW_AGENT_DESCRIPTION = "Stock Management Workflow Agent"


class StockItem(StrictModel):
    sku: str
    product_name: str
    category_name: str
    stock_level: int
    cost: float


class StockItemCollection(StrictModel):
    items: list[StockItem]


class StockExtractorResult(StrictModel):
    context: str
    messages: list[str]
    collection: StockItemCollection


class RestockResult(StrictModel):
    items: list[StockItem]
    summary: str


DEFAULT_MODEL = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5-mini")


class StockExtractor(Executor):
    """Custom executor that extracts stock information from messages."""

    agent: Agent

    def __init__(self, client: AzureAIClient, tools: Any | Sequence[Any], agent_suffix: str = ""):
        _id = "stock-extractor-agent" + agent_suffix
        self.agent = client.as_agent(
            name=_id,
            description=WORKFLOW_AGENT_DESCRIPTION,
            instructions=(
                "You determine strategies for restocking items. "
                "Consult the tools for stock levels and prioritise which items to restock first."
            ),
            model_id=DEFAULT_MODEL,
            tools=tools,
            tool_choice='required',
            store=True,
        )
        super().__init__(id=_id)

    @handler
    async def handle(self, message: Message, ctx: WorkflowContext[StockExtractorResult]) -> None:
        """Extract department data"""
        response = await self.agent.run(message, response_format=StockItemCollection)
        value = cast(StockItemCollection, response.value)
        result = StockExtractorResult(
            context=message.text,
            messages=[message.text for message in response.messages if message.text.strip()],
            collection=value,
        )
        await ctx.send_message(result)


class ContextExecutor(Executor):
    """Custom executor that provides context about the user request."""

    agent: Agent

    def __init__(self, client: AzureAIClient, agent_suffix: str = ""):
        _id = "stock-context-agent" + agent_suffix
        self.agent = client.as_agent(
            name=_id,
            description=WORKFLOW_AGENT_DESCRIPTION,
            instructions=("You look at the context to prioritize restocking items."),
            model_id=DEFAULT_MODEL,
            store=True,
        )
        # Associate the agent with this executor node. The base Executor stores it on self.agent.
        super().__init__(id=_id)

    @handler
    async def handle(self, stock_result: StockExtractorResult, ctx: WorkflowContext[StockExtractorResult]) -> None:
        m = "You look at the context to prioritize restocking items. Original Request:\n" + stock_result.context
        m += "\n\nCurrent Items:\n" + stock_result.collection.model_dump_json(indent=2)
        response = await self.agent.run(m, response_format=StockItemCollection)
        value = cast(StockItemCollection, response.value)
        context_result = StockExtractorResult(
            context=stock_result.context,
            messages=[message.text for message in response.messages if message.text.strip()],
            collection=value,
        )
        await ctx.send_message(context_result)


class Summarizer(Executor):
    """Custom executor that owns a summarization agent and completes the workflow.

    This class demonstrates:
    - Consuming a typed payload produced upstream.
    - Yielding the final text outcome to complete the workflow.
    """

    agent: Agent

    def __init__(self, client: AzureAIClient, agent_suffix: str = ""):
        _id = "stock-summarizer-agent" + agent_suffix
        # Create a domain specific agent that summarizes content.
        self.agent = client.as_agent(
            id=_id,
            name=_id,
            description=WORKFLOW_AGENT_DESCRIPTION,
            instructions=(
                "You are an excellent workflow summarizer. You summarize the restocking task and what the user asked for into an overview. "
                "Do not list the items one by one as the user will get these in the final output."
                "Look at the specific user instructions and context to provide a tailored summary."
            ),
            model_id=DEFAULT_MODEL,
            store=True,
        )
        super().__init__(id=_id)

    @handler
    async def handle(
        self, stock_result: StockExtractorResult, ctx: WorkflowContext[list[Message], RestockResult]
    ) -> None:
        """Review the full conversation transcript and complete with a final string.

        This node consumes all messages so far. It uses its agent to produce the final text,
        then signals completion by yielding the output.
        """
        response = await self.agent.run(stock_result.messages)
        await ctx.send_message(response.messages)
        await ctx.yield_output(RestockResult(items=stock_result.collection.items, summary=response.text))


def build_workflow(
    credential: AsyncTokenCredential | None = None,
    project_endpoint: str | None = None,
    mcp: Any | Sequence[Any] | None = None,
    agent_suffix: str = "",
    user_token: str | None = None,
) -> Workflow:
    if credential is None:
        credential = DefaultAzureCredential(
            exclude_shared_token_cache_credential=True,
            exclude_visual_studio_code_credential=True,
        )
    project_endpoint = project_endpoint or os.getenv("AZURE_AI_PROJECT_ENDPOINT")

    if mcp is None:
        # Use user token if provided, otherwise fall back to DEV_GUEST_TOKEN for local dev
        auth_token = user_token or os.getenv('DEV_GUEST_TOKEN', 'dev-guest-token')
        mcp = MCPStreamableHTTPToolOTEL(
            name="FinanceMCP",
            url=os.getenv("FINANCE_MCP_HTTP", "http://localhost:8002") + "/mcp",
            headers={"Authorization": f"Bearer {auth_token}"},
            load_prompts=False,
            request_timeout=30,
        )

    stock = StockExtractor(
        AzureAIClient(credential=credential, project_endpoint=project_endpoint, model_deployment_name=DEFAULT_MODEL),
        tools=mcp,
        agent_suffix=agent_suffix,
    )
    context = ContextExecutor(
        AzureAIClient(credential=credential, project_endpoint=project_endpoint, model_deployment_name=DEFAULT_MODEL),
        agent_suffix=agent_suffix,
    )
    summarizer = Summarizer(
        AzureAIClient(credential=credential, project_endpoint=project_endpoint, model_deployment_name=DEFAULT_MODEL),
        agent_suffix=agent_suffix,
    )

    workflow = (
        WorkflowBuilder(
            start_executor=stock,
            name="Restocking Workflow",
            description="A workflow to manage stock restocking based on user requests.",
        )
        .add_edge(stock, context)
        .add_edge(context, summarizer)
        .build()
    )

    return workflow

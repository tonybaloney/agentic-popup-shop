# Copyright (c) Microsoft. All rights reserved.
import os
from dataclasses import dataclass
from typing import Any, Never, Sequence, cast

from agent_framework import (
    AgentExecutor,
    AgentExecutorRequest,
    AgentExecutorResponse,
    Agent,
    Case,
    Default,
    Executor,
    Message,
    Workflow,
    WorkflowBuilder,
    WorkflowContext,
    handler,
)
from agent_framework_azure_ai import AzureAIClient
from azure.core.credentials_async import AsyncTokenCredential
from azure.identity.aio import DefaultAzureCredential

from zava_shop_agents import MCPStreamableHTTPToolOTEL, StrictModel

DEFAULT_MODEL = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5-mini")


class CompetitiveResult(StrictModel):
    is_competitive: bool


def is_competitive():
    def condition(message: Any) -> bool:
        # Only match when the upstream payload is a DetectionResult with the expected decision.
        return isinstance(message, CompetitiveResult) and message.is_competitive

    return condition


class DispatchToExperts(Executor):
    """Dispatches the incoming prompt to all expert agent executors (fan-out)."""

    _expert_ids: list[str]

    def __init__(self, expert_ids: list[str], id: str | None = None):
        super().__init__(id=id or "dispatch_to_experts")
        self._expert_ids = expert_ids

    @handler
    async def dispatch(self, prompt: str | Message, ctx: WorkflowContext[AgentExecutorRequest]) -> None:
        # Wrap the incoming prompt as a user message for each expert and request a response.
        if isinstance(prompt, str):
            initial_message = Message(role="user", contents=[prompt])
        else:
            initial_message = prompt
        for expert_id in self._expert_ids:
            await ctx.send_message(
                AgentExecutorRequest(messages=[initial_message], should_respond=True),
                target_id=expert_id,
            )


@dataclass
class AggregatedInsights:
    """Structured output from the aggregator."""

    compliance: str
    commercial: str
    procurement: str

    def __str__(self) -> str:
        return (
            f"Compliance Findings:\n{self.compliance}\n\n"
            f"Commercial Angle:\n{self.commercial}\n\n"
            f"Procurement Notes:\n{self.procurement}\n"
        )


class AggregateInsightsResult(CompetitiveResult):
    aggregated_insights: AggregatedInsights

    def __str__(self) -> str:
        return self.aggregated_insights.__str__()


LEGAL_COMPLIANCE_EXPERT_ID = "Legal/Compliance Researcher"
COMMERCIAL_EXPERT_ID = "Commercial Researcher"
PROCUREMENT_EXPERT_ID = "Procurement Researcher"

WORKFLOW_AGENT_DESCRIPTION = "Supplier Review Workflow Agent"

class AggregateInsights(Executor):
    """Aggregates expert agent responses into a single consolidated result (fan-in)."""

    agent: Agent

    def __init__(
        self,
        expert_ids: list[str],
        client: AzureAIClient,
        tools: Any | Sequence[Any],
        agent_suffix: str = "",
    ):
        _id = "aggregate-insights-agent" + agent_suffix
        self._expert_ids = expert_ids

        self.agent = client.as_agent(
            name=_id,
            description=WORKFLOW_AGENT_DESCRIPTION,
            instructions="You are an expert evaluator. Given the consolidated insights, determine if the proposal is competitive or not competitive.",
            model_id=DEFAULT_MODEL,
            tools=tools,
            tool_choice="required",
            store=True,
        )
        super().__init__(id=_id)

    @handler
    async def aggregate(
        self, results: list[AgentExecutorResponse], ctx: WorkflowContext[AggregateInsightsResult]
    ) -> None:
        # Map responses to text by executor id for a simple, predictable demo.
        by_id: dict[str, str] = {}
        for r in results:
            # AgentExecutorResponse.agent_run_response.text contains concatenated assistant text
            by_id[r.executor_id] = r.agent_run_response.text

        compliance_text = by_id.get(LEGAL_COMPLIANCE_EXPERT_ID, "")
        commercial_text = by_id.get(COMMERCIAL_EXPERT_ID, "")
        procurement_text = by_id.get(PROCUREMENT_EXPERT_ID, "")

        aggregated = AggregatedInsights(
            compliance=compliance_text,
            commercial=commercial_text,
            procurement=procurement_text,
        )

        # Provide a readable, consolidated string as the final workflow result.
        consolidated = (
            "Considering the consolidated Insights, decide whether this proposal is competitive or not competitive\n"
            "====================\n\n"
            f"Compliance Findings:\n{aggregated.compliance}\n\n====================\n\n"
            f"Commercial Angle:\n{aggregated.commercial}\n\n====================\n\n"
            f"Procurement Notes:\n{aggregated.procurement}\n"
        )

        response = await self.agent.run(consolidated, response_format=CompetitiveResult)
        value = cast(CompetitiveResult, response.value)
        result = AggregateInsightsResult(is_competitive=value.is_competitive, aggregated_insights=aggregated)

        await ctx.send_message(result)


class NegotiatorSummarizerExecutor(Executor):
    agent: Agent

    def __init__(self, client: AzureAIClient, tools: Any | Sequence[Any], agent_suffix: str = ""):
        _id = "negotiator-summarizer" + agent_suffix
        self.agent = client.as_agent(
            name=_id,
            description=WORKFLOW_AGENT_DESCRIPTION,
            instructions=(
                "You are a skilled negotiator. Given that the proposal is competitive, draft a negotiation strategy and summarize key points."
                "Consult with existing suppliers from the tools provided if needed to optimize terms."
            ),
            model_id=DEFAULT_MODEL,
            tools=tools,
            tool_choice="required",
            store=True,
        )
        super().__init__(id=_id)

    @handler
    async def handle(self, request: AggregateInsightsResult, ctx: WorkflowContext[Never, str]) -> None:
        response = await self.agent.run(str(request))

        await ctx.yield_output(response.text)


class ReviewAndDismissExecutor(Executor):
    agent: Agent

    def __init__(self, client: AzureAIClient, tools: Any | Sequence[Any], agent_suffix: str = ""):
        _id = "review-and-dismiss" + agent_suffix
        self.agent = client.as_agent(
            name=_id,
            description=WORKFLOW_AGENT_DESCRIPTION,
            instructions=(
                "You have been asked to review a supplier proposal that is not competitive. Provide a summary of the reasons and suggest dismissal points."
            ),
            model_id=DEFAULT_MODEL,
            tools=tools,
            tool_choice="required",
            store=True,
        )
        super().__init__(id=_id)

    @handler
    async def handle(self, request: AggregateInsightsResult, ctx: WorkflowContext[Never, str]) -> None:
        response = await self.agent.run(str(request))

        await ctx.yield_output(response.text)


def build_workflow(
    credential: AsyncTokenCredential | None = None,
    project_endpoint: str | None = None,
    tools: Sequence[Any] | None = None,
    agent_suffix: str = "",
) -> Workflow:
    if credential is None:
        credential = DefaultAzureCredential(
            exclude_shared_token_cache_credential=True,
            exclude_visual_studio_code_credential=True,
        )
    project_endpoint = project_endpoint or os.getenv("AZURE_AI_PROJECT_ENDPOINT")

    if tools is None:
        tools = [
            MCPStreamableHTTPToolOTEL(
                name="SupplierMCP",
                url=os.getenv("SUPPLIER_MCP_HTTP", "http://localhost:8001") + "/mcp",
                headers={"Authorization": f"Bearer {os.getenv('DEV_GUEST_TOKEN', 'dev-guest-token')}"},
                load_tools=True,
                load_prompts=False,
                request_timeout=30,
            ),
            MCPStreamableHTTPToolOTEL(
                name="FinanceMCP",
                url=os.getenv("FINANCE_MCP_HTTP", "http://localhost:8002") + "/mcp",
                headers={"Authorization": f"Bearer {os.getenv('DEV_GUEST_TOKEN', 'dev-guest-token')}"},
                load_tools=True,
                load_prompts=False,
                request_timeout=30,
            ),
        ]

    compliance = AgentExecutor(
        AzureAIClient(
            credential=credential, project_endpoint=project_endpoint, model_deployment_name=DEFAULT_MODEL
        ).as_agent(
            name='legal-compliance-researcher' + agent_suffix,
            description=WORKFLOW_AGENT_DESCRIPTION,
            instructions=(
                "You're an expert legal and compliance researcher. You review a proposal and provide feedback on behalf of Zava stores."
                "Use the provided tools to find out information about other suppliers' ESG and compliance status."
            ),
            model_id=DEFAULT_MODEL,
            tools=tools,
        ),
        id=LEGAL_COMPLIANCE_EXPERT_ID,
    )
    commercial = AgentExecutor(
        AzureAIClient(
            credential=credential, project_endpoint=project_endpoint, model_deployment_name=DEFAULT_MODEL
        ).as_agent(
            name='commercial-researcher' + agent_suffix,
            description=WORKFLOW_AGENT_DESCRIPTION,
            instructions=(
                "You are an expert commercial analyst. Evaluate supplier proposals for market competitiveness and value."
                "Use the supplied tools to understand our existing stock levels, prices and demand."
            ),
            model_id=DEFAULT_MODEL,
            tools=tools,
        ),
        id=COMMERCIAL_EXPERT_ID,
    )
    procurement = AgentExecutor(
        AzureAIClient(
            credential=credential, project_endpoint=project_endpoint, model_deployment_name=DEFAULT_MODEL
        ).as_agent(
            name='procurement-researcher' + agent_suffix,
            description=WORKFLOW_AGENT_DESCRIPTION,
            instructions=(
                "You are an expert procurement analyst. Analyze supplier proposals for cost-effectiveness and strategic fit."
                "Use the supplied tools to check existing supplier contracts and performance."
            ),
            model_id=DEFAULT_MODEL,
            tools=tools,
        ),
        id=PROCUREMENT_EXPERT_ID,
    )

    negotiator = NegotiatorSummarizerExecutor(
        agent_suffix=agent_suffix,
        client=AzureAIClient(
            credential=credential, project_endpoint=project_endpoint, model_deployment_name=DEFAULT_MODEL
        ),
        tools=tools,
    )

    review_and_dismiss = ReviewAndDismissExecutor(
        agent_suffix=agent_suffix,
        client=AzureAIClient(
            credential=credential, project_endpoint=project_endpoint, model_deployment_name=DEFAULT_MODEL
        ),
        tools=tools,
    )

    expert_ids = [compliance.id, commercial.id, procurement.id]

    dispatcher = DispatchToExperts(expert_ids=expert_ids, id="proposal-dispatcher" + agent_suffix)
    aggregator = AggregateInsights(
        expert_ids=expert_ids,
        client=AzureAIClient(
            credential=credential, project_endpoint=project_endpoint, model_deployment_name=DEFAULT_MODEL
        ),
        tools=tools,
        agent_suffix=agent_suffix,
    )

    workflow = (
        WorkflowBuilder(
            start_executor=dispatcher,
            name="Supplier Review Workflow",
            description="Workflow to review supplier proposals and determine competitiveness.",
        )
        .add_fan_out_edges(dispatcher, [compliance, commercial, procurement])
        .add_fan_in_edges([compliance, commercial, procurement], aggregator)
        .add_switch_case_edge_group(
            aggregator,
            [
                Case(condition=is_competitive(), target=negotiator),
                Default(target=review_and_dismiss),
            ],
        )
        .build()
    )

    return workflow

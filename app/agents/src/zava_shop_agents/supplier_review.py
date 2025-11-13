
from dataclasses import dataclass

from pydantic import BaseModel
from agent_framework import (
    AgentExecutor,
    AgentExecutorRequest,
    AgentExecutorResponse,
    ChatMessage,
    Executor,
    Role,
    WorkflowBuilder,
    WorkflowContext,
    Case,
    Default,
    handler,
)
from typing import Any, Never
import os
from agent_framework.azure import AzureOpenAIChatClient
from zava_shop_agents import MCPStreamableHTTPToolOTEL

chat_client = AzureOpenAIChatClient(api_key=os.environ.get("AZURE_OPENAI_API_KEY_GPT5"),
                                    endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT_GPT5"),
                                    deployment_name=os.environ.get("AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5"),
                                    api_version=os.environ.get("AZURE_OPENAI_ENDPOINT_VERSION_GPT5", "2024-02-15-preview"))

supplier_mcp_tools = MCPStreamableHTTPToolOTEL(
    name="SupplierMCP",
    url=os.getenv("SUPPLIER_MCP_HTTP", "http://localhost:8001") + "/mcp",
    headers={
         "Authorization": f"Bearer {os.getenv('DEV_GUEST_TOKEN','dev-guest-token')}"
    },
    load_tools=True,
    load_prompts=False,
    request_timeout=30,
)

finance_mcp = MCPStreamableHTTPToolOTEL(
    name="FinanceMCP",
    url=os.getenv("FINANCE_MCP_HTTP", "http://localhost:8002") + "/mcp",
    headers={
         "Authorization": f"Bearer {os.getenv('DEV_GUEST_TOKEN','dev-guest-token')}"
    },
    load_tools=True,
    load_prompts=False,
    request_timeout=30,
)

class CompetitiveResult(BaseModel):
    is_competitive: bool

def is_competitive():
    def condition(message: Any) -> bool:
        # Only match when the upstream payload is a DetectionResult with the expected decision.
        return isinstance(message, CompetitiveResult) and message.is_competitive

    return condition

class DispatchToExperts(Executor):
    """Dispatches the incoming prompt to all expert agent executors (fan-out)."""

    def __init__(self, expert_ids: list[str], id: str | None = None):
        super().__init__(id=id or "dispatch_to_experts")
        self._expert_ids = expert_ids

    @handler
    async def dispatch(self, prompt: str, ctx: WorkflowContext[AgentExecutorRequest]) -> None:
        # Wrap the incoming prompt as a user message for each expert and request a response.
        initial_message = ChatMessage(Role.USER, text=prompt)
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


class AggregateInsights(Executor):
    """Aggregates expert agent responses into a single consolidated result (fan-in)."""

    def __init__(self, expert_ids: list[str], id: str | None = None):
        super().__init__(id=id or "aggregate_insights")
        self._expert_ids = expert_ids

    @handler
    async def aggregate(self, results: list[AgentExecutorResponse], ctx: WorkflowContext[AggregateInsightsResult]) -> None:
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

        chat_client_agent = chat_client.create_agent(
            instructions=(
                "You are an expert evaluator. Given the consolidated insights, determine if the proposal is competitive or not competitive."
            ),
            tools=[supplier_mcp_tools],
        )
        response = await chat_client_agent.run(consolidated, response_format=CompetitiveResult)

        result = AggregateInsightsResult(is_competitive=response.value.is_competitive, aggregated_insights=aggregated)

        await ctx.send_message(result)

compliance = AgentExecutor(
    chat_client.create_agent(
        instructions=(
            "You're an expert legal and compliance researcher. You review a proposal and provide feedback on behalf of Zava stores." \
            "Use the provided tools to find out information about other suppliers' ESG and compliance status."
        ),
        tools=[supplier_mcp_tools],
    ),
    id=LEGAL_COMPLIANCE_EXPERT_ID,
)
commercial = AgentExecutor(
    chat_client.create_agent(
        instructions=(
            "You are an expert commercial analyst. Evaluate supplier proposals for market competitiveness and value." \
            "Use the supplied tools to understand our existing stock levels, prices and demand."
        ),
        tools=[finance_mcp],
    ),
    id=COMMERCIAL_EXPERT_ID,
)
procurement = AgentExecutor(
    chat_client.create_agent(
        instructions=(
            "You are an expert procurement analyst. Analyze supplier proposals for cost-effectiveness and strategic fit."
            "Use the supplied tools to check existing supplier contracts and performance."
        ),
        tools=[supplier_mcp_tools],
    ),
    id=PROCUREMENT_EXPERT_ID,
)

expert_ids = [compliance.id, commercial.id, procurement.id]

dispatcher = DispatchToExperts(expert_ids=expert_ids, id="Proposal Dispatcher")
aggregator = AggregateInsights(expert_ids=expert_ids, id="Competitive Analysis Aggregator")


class NegotiatorSummarizerExecutor(Executor):
    @handler
    async def handle(self, request: AggregateInsightsResult, ctx: WorkflowContext[Never, str]) -> AgentExecutorResponse:
        chat_client_agent = chat_client.create_agent(
            instructions=(
                "You are a skilled negotiator. Given that the proposal is competitive, draft a negotiation strategy and summarize key points." \
                "Consult with existing suppliers from the tools provided if needed to optimize terms."
            ),
            tools=[supplier_mcp_tools],
        )
        response = await chat_client_agent.run(str(request))

        await ctx.yield_output(response.text)


class ReviewAndDismissExecutor(Executor):
    @handler
    async def handle(self, request: AggregateInsightsResult, ctx: WorkflowContext[Never, str]) -> AgentExecutorResponse:
        chat_client_agent = chat_client.create_agent(
            instructions=(
                "You have been asked to review a supplier proposal that is not competitive. Provide a summary of the reasons and suggest dismissal points."
            ),
            tools=[supplier_mcp_tools],
        )
        response = await chat_client_agent.run(str(request))

        await ctx.yield_output(response.text)


negotiator = NegotiatorSummarizerExecutor(
    id="Negotiator & Summarizer",
)

review_and_dismiss = ReviewAndDismissExecutor(
    id="Review & Dismiss",
)

workflow = (
    WorkflowBuilder(name="Supplier Review Workflow")
    .set_start_executor(dispatcher)
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

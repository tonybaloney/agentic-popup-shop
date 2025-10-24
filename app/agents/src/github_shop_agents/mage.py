import logging
import asyncio
import os
from agent_framework import (
    ChatAgent,
    MCPStreamableHTTPTool,
    MagenticBuilder,
)
from agent_framework.azure import AzureOpenAIChatClient

from agent_framework import (
    MagenticCallbackEvent,
    MagenticFinalResultEvent,
    MagenticOrchestratorMessageEvent,
    MagenticCallbackMode,
)


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

chat_client = AzureOpenAIChatClient(api_key=os.environ.get("AZURE_OPENAI_API_KEY_GPT5"),
                                    endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT_GPT5"),
                                    deployment_name=os.environ.get("AZURE_OPENAI_MODEL_DEPLOYMENT_NAME_GPT5"),
                                    api_version=os.environ.get("AZURE_OPENAI_ENDPOINT_VERSION_GPT5", "2024-02-15-preview"))


async def get_tool_list(tool: MCPStreamableHTTPTool) -> str:
    tool_suffix = ""
    async with tool as tools:
        await tools.load_tools()
        for func in tools.functions:
             tool_suffix += f"\n### {func.name}\n{func.description}\n------------------------\n"
    return tool_suffix

supplier_mcp_tools = MCPStreamableHTTPTool(
    name="SupplierMCP",
    url=os.getenv("SUPPLIER_MCP_HTTP", "http://localhost:8001") + "/mcp",
    headers={
         "Authorization": f"Bearer {os.getenv('DEV_GUEST_TOKEN','dev-guest-token')}"
    },
    load_tools=True,
    load_prompts=False,
    request_timeout=30,
)
supplier_tools = asyncio.run(get_tool_list(supplier_mcp_tools))

supplier_agent = ChatAgent(
    name="SupplierAgent",
    description=f" Use Defaults. Do not stop to clarify. You are a helpful assistant that integrates with the backend supplier data. \n\nYou have the following capabilities: \n{supplier_tools}",
    instructions="You solve questions using supplier data and the tools provided.",
    chat_client=chat_client,
    tools=supplier_mcp_tools,
)


async def on_event(event: MagenticCallbackEvent) -> None:
        """
        The `on_event` callback processes events emitted by the workflow.
        Events include: orchestrator messages, agent delta updates, agent messages, and final result events.
        """
        if isinstance(event, MagenticOrchestratorMessageEvent):
            print(f"\n[ORCH:{event.kind}]\n\n{getattr(event.message, 'text', '')}\n{'-' * 26}")
        elif isinstance(event, MagenticFinalResultEvent):
            print("\n" + "=" * 50)
            print("FINAL RESULT:")
            print("=" * 50)
            if event.message is not None:
                print(event.message.text)
            print("=" * 50)

workflow = (
    MagenticBuilder()
    .participants(supplier=supplier_agent)
    # .with_plan_review()
    .on_event(on_event, mode=MagenticCallbackMode.STREAMING)
    .with_standard_manager(
        chat_client=chat_client,
        max_round_count=5,
        max_stall_count=3,
        max_reset_count=1,
    )
    .build()
)

"""Build Agent using Microsoft Agent Framework in Python
# Run this python script
> pip install agent-framework --pre
> python <this-script-path>.py
"""

import asyncio
import os

from agent_framework import ChatAgent, MCPStdioTool, MCPStreamableHTTPTool, ToolProtocol
from agent_framework_azure_ai import AzureAIAgentClient
from agent_framework.openai import OpenAIChatClient
from openai import AsyncOpenAI
from azure.identity.aio import DefaultAzureCredential

# Azure AI Foundry Agent Configuration
ENDPOINT = "https://anthonyshaw-ignitetesting-resour.services.ai.azure.com/api/projects/anthonyshaw-ignitetesting"
MODEL_DEPLOYMENT_NAME = "gpt-5-mini"

AGENT_NAME = "mcp-agent"
AGENT_INSTRUCTIONS = "You are a retail analyst analyzing product performance. \nYour task: retrieve the top 5 selling products for a specific store over the last 21 days. Use the finance MCP tools to get revenue, units sold, and SKU for each product. Limit results to exactly 5 products and order by units sold in descending order. Always respond using the provided response schema."

# User inputs for the conversation
USER_INPUTS = [
    "Top 5 selling products for store_id 1 over the last 21 days. Use the finance MCP tools to retrieve revenue, units sold, and SKU. Limit results to 5 and order by units sold descending.",
]

def create_mcp_tools() -> list[ToolProtocol]:
    return [
        MCPStreamableHTTPTool(
            name="zava-finance-agent".replace("-", "_"),
            description="MCP server for zava-finance-agent",
            url="http://localhost:28001/mcp",
            headers={
                "Authorization": "Bearer dev-guest-token",
            }
        ),
    ]

async def main() -> None:
    async with (
        DefaultAzureCredential() as credential,
        ChatAgent(
            chat_client=AzureAIAgentClient(
                project_endpoint=ENDPOINT,
                model_deployment_name=MODEL_DEPLOYMENT_NAME,
                async_credential=credential,
                agent_name=AGENT_NAME,
                agent_id=None,  # Since no Agent ID is provided, the agent will be automatically created and deleted after getting response
            ),
            instructions=AGENT_INSTRUCTIONS,
            tools=[
                *create_mcp_tools(),
            ],
        ) as agent
    ):
        # Create a new thread that will be reused
        thread = agent.get_new_thread()

        # Process user messages
        for user_input in USER_INPUTS:
            print(f"\n# User: '{user_input}'")
            async for chunk in agent.run_stream([user_input], thread=thread):
                if chunk.text:
                    print(chunk.text, end="")
                elif (
                    chunk.raw_representation
                    and chunk.raw_representation.raw_representation
                    and hasattr(chunk.raw_representation.raw_representation, "status")
                    and hasattr(chunk.raw_representation.raw_representation, "type")
                    and chunk.raw_representation.raw_representation.status == "completed"
                    and hasattr(chunk.raw_representation.raw_representation, "step_details")
                    and hasattr(chunk.raw_representation.raw_representation.step_details, "tool_calls")
                ):
                    print("")
                    print("Tool calls: ", chunk.raw_representation.raw_representation.step_details.tool_calls)
            print("")
        
        print("\n--- All tasks completed successfully ---")

    # Give additional time for all async cleanup to complete
    await asyncio.sleep(1.0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nProgram interrupted by user")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Program finished.")

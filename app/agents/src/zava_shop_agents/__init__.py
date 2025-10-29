from opentelemetry.trace import get_current_span
from contextlib import _AsyncGeneratorContextManager
from typing import Any
from agent_framework import (
    MCPStreamableHTTPTool,
)
import asyncio


class MCPStreamableHTTPToolOTEL(MCPStreamableHTTPTool):
    def get_mcp_client(self) -> _AsyncGeneratorContextManager[Any, None]:
        span_ctx = get_current_span().get_span_context()
        self.headers["traceparent"] = f"00-{span_ctx.trace_id:032x}-{span_ctx.span_id:016x}-01"
        return super().get_mcp_client()

def get_or_create_eventloop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop

from opentelemetry.instrumentation.auto_instrumentation import initialize
initialize()

from agent_framework.devui import serve
import os

from .stock import workflow as stock_workflow
from .mage import workflow as magentic_workflow

def main():
    port = os.environ.get("PORT", 8090)

    # Launch server with the workflow
    serve(entities=[stock_workflow, magentic_workflow], port=int(port), auto_open=True, tracing_enabled=True)


if __name__ == "__main__":
    main()

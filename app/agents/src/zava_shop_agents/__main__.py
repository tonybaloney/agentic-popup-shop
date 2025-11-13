from agent_framework.devui import serve
import os

from .stock import workflow as stock_workflow
from .mage import workflow as magentic_workflow
from .supplier_review import workflow as supplier_review_workflow
from .marketing import get_workflow as get_marketing_workflow
from .insights import get_workflow as get_insights_workflow

def main():
    port = os.environ.get("PORT", 8090)

    # Launch server with the workflow
    serve(entities=[stock_workflow, magentic_workflow, supplier_review_workflow, get_marketing_workflow(), get_insights_workflow()], port=int(port), auto_open=True, tracing_enabled=True)


if __name__ == "__main__":
    main()

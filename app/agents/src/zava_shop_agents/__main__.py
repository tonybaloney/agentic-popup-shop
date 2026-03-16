from agent_framework.devui import serve
import os

from .stock import build_workflow as stock_workflow
from .supplier_review import build_workflow as supplier_review_workflow
from .insights import build_workflow as insights_workflow
from .admin_insights import build_workflow as admin_insights_workflow
from .returns import build_workflow as returns_workflow

from azure.identity.aio import DefaultAzureCredential


def main():
    port = os.environ.get("PORT", 8090)

    credential = DefaultAzureCredential()

    # Launch server with the workflow
    serve(
        entities=[
            stock_workflow(credential=credential),
            supplier_review_workflow(credential=credential),
            insights_workflow(credential=credential),
            admin_insights_workflow(credential=credential),
            returns_workflow(credential=credential),
        ],
        port=int(port),
        auto_open=False,
    )

if __name__ == "__main__":
    main()

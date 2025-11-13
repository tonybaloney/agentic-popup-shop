import argparse
from datetime import datetime, timezone
import pathlib
import json

from pydantic import BaseModel
from agent_framework import (ChatMessage,
                             ExecutorInvokedEvent,
                             ExecutorCompletedEvent,
                             ExecutorFailedEvent,
                             WorkflowOutputEvent,
                             WorkflowStartedEvent)
import asyncio
import dotenv
from opentelemetry import trace
import os

dotenv.load_dotenv()
from .stock import workflow

async def process_batch(store_id: int, repeat: int, input_path: pathlib.Path, output_path: pathlib.Path, dry_run: bool):
    # Placeholder for the actual batch processing logic
    print(f"Processing batch for store {store_id} with repeat={repeat}, input={input_path}, output={output_path}, dry_run={dry_run}")

    with input_path.open("r") as f:
        prompts = f.readlines()
        # strip and filter empty lines
        prompts = [p.strip() for p in prompts if p.strip()]

    results = []

    for prompt in prompts:
        for _ in range(repeat):
            if dry_run:
                print(f"[Dry Run] Would process prompt: {prompt}")
            else:
                with trace.get_tracer(__name__).start_as_current_span("batch_process") as span:
                    trace_id = format(span.get_span_context().trace_id, '032x')
                    span_id = format(span.get_span_context().span_id, '016x')
                # Run the workflow and stream events
                # Add store_id to the message if provided
                if store_id:
                    full_message = f"{prompt}\n\nStore ID: {store_id}"
                else:
                    full_message = prompt

                input: ChatMessage = ChatMessage(role='user', text=full_message)

                try:
                    async for event in workflow.run_stream(input):
                        now = datetime.now(timezone.utc).isoformat()
                        event_data = None
                        if isinstance(event, WorkflowStartedEvent):
                            event_data = {
                                "type": "workflow_started",
                                "event": str(event.data),
                                "timestamp": now
                            }
                        elif isinstance(event, WorkflowOutputEvent):
                            # Capture the workflow output (markdown result)
                            if isinstance(event.data, BaseModel):
                                workflow_output = event.data.model_dump()
                            else:
                                workflow_output = str(event.data)
                            event_data = {
                                "type": "workflow_output",
                                "event": workflow_output,
                                "timestamp": now
                            }
                        elif isinstance(event, ExecutorInvokedEvent):
                            event_data = {
                                "type": "step_started",
                                "event": event.data,
                                "id": event.executor_id,
                                "timestamp": now
                            }
                        elif isinstance(event, ExecutorCompletedEvent):
                            event_data = {
                                "type": "step_completed",
                                "event": event.data,
                                "id": event.executor_id,
                                "timestamp": now
                            }
                        elif isinstance(event, ExecutorFailedEvent):
                            event_data = {
                                "type": "step_failed",
                                "event": event.details.message,
                                "id": event.executor_id,
                                "timestamp": now
                            }
                        # else:
                        #     # Stream each workflow event to the frontend
                        #     event_data = {
                        #         "type": "event",
                        #         "event": str(event),
                        #         "timestamp": now
                        #     }
                        if event_data:
                            event_data['input_prompt'] = full_message
                            event_data['trace_id'] = trace_id
                            event_data['span_id'] = span_id
                            results.append(event_data)

                except Exception as e:
                    print(f"Error processing prompt '{prompt}': {e}")
                    continue

    if not dry_run:
        with output_path.open("w") as f:
            json.dump(results, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run batch processes for Zava Shop Agents.")
    parser.add_argument(
        "--store",
        type=int,
        required=True,
        choices=[1, 2],
        default=1,
        help="The store ID to run the batch process for.",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of times to repeat the batch process.",
    )
    parser.add_argument(
        "--inputs",
        type=pathlib.Path,
        required=True,
        help="Path to the input data. Each line will be considered a different prompt.",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        required=True,
        help="Path to the output results file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="If set, the batch process will not run the workflow.",
    )

    if os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"]:
        print("Configuring application insights")
        from azure.monitor.opentelemetry import configure_azure_monitor
        # Configure Azure monitor collection telemetry pipeline
        configure_azure_monitor()

    args = parser.parse_args()
    asyncio.run(process_batch(
        store_id=args.store,
        repeat=args.repeat,
        input_path=args.inputs,
        output_path=args.output,
        dry_run=args.dry_run,
    ))

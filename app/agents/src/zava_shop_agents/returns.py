# Copyright (c) Microsoft. All rights reserved.
"""
Product Return Workflow Agent

A deterministic workflow for processing customer product returns.
Supports full-order and partial returns. All returns require a photo
of the items being returned, verified by a multimodal AI model.
All returns are validated against the Zava Shop returns policy.

Workflow:
  ReturnIntakeExecutor (classify full vs partial, extract order/items)
    → PolicyValidationExecutor (validate reason against returns policy)
        ├── [valid] → PhotoVerificationExecutor (gpt-5-mini multimodal)
        │                → ReturnApprovalExecutor
        └── [invalid reason] → yields denied ReturnApprovalResult with feedback
"""

import base64
import os
from enum import Enum
from typing import Any, Literal, Never, Optional, Sequence, cast

from agent_framework import (
    Agent,
    Content,
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
from pydantic import BaseModel, Field

from zava_shop_agents import StrictModel

WORKFLOW_AGENT_DESCRIPTION = "Product Return Workflow Agent"

# Use gpt-5-mini for photo verification (multimodal)
MULTIMODAL_MODEL = os.environ.get("AZURE_AI_MULTIMODAL_MODEL_DEPLOYMENT_NAME", "gpt-5-mini")
# Use the default model for text-only tasks
DEFAULT_MODEL = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-5-mini")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class ReturnType(str, Enum):
    """Type of return."""
    FULL = "full"
    PARTIAL = "partial"


# Literal type for structured output schemas (avoids $ref issues with Azure AI)
ReturnTypeLiteral = Literal["full", "partial"]


class ReturnWorkflowInput(BaseModel):
    """Structured input to the return workflow.

    Bundles the customer message together with a photo so both
    travel through the workflow entry-point.
    """
    message: str = Field(..., description="The customer's return-request message")
    photo_base64: str = Field(default="", description="Base64-encoded photo of items being returned")
    photo_mime_type: str = Field(default="image/jpeg", description="MIME type of the photo")


class ReturnItemRequest(StrictModel):
    """A single item the customer wants to return."""
    product_name: str = Field(..., description="Name of the product")
    sku: str = Field(..., description="SKU of the product, or empty string if not known")
    quantity: int = Field(..., description="Number of units to return")


class ReturnIntakeResult(StrictModel):
    """Output of the intake executor – captures what the customer wants to return."""
    order_id: int = Field(..., description="The order ID for the return")
    return_type: ReturnTypeLiteral = Field(..., description="Whether this is a full or partial return")
    items: list[ReturnItemRequest] = Field(..., description="Items requested for return")
    reason: str = Field(..., description="Customer-stated reason for the return")
    original_message: str = Field(..., description="The original customer message")


class PhotoVerificationResult(StrictModel):
    """Result of AI photo verification for return items."""
    verified: bool = Field(..., description="Whether the photo shows the expected items ready for return")
    items_detected: list[str] = Field(..., description="Items detected in the photo")
    confidence_notes: str = Field(..., description="Explanation of the verification decision")


class PolicyValidationResult(StrictModel):
    """Result of validating the return reason against the returns policy."""
    reason_valid: bool = Field(..., description="Whether the stated reason is covered by the returns policy")
    policy_category: str = Field(..., description="The matching policy category, or 'none' if no match")
    feedback: str = Field(..., description="Explanation for the customer about why their reason was accepted or rejected")


class ReturnApprovalResult(StrictModel):
    """Final output of the return workflow."""
    approved: bool = Field(..., description="Whether the return is approved")
    return_type: ReturnTypeLiteral = Field(..., description="Full or partial return")
    order_id: int = Field(..., description="The order ID")
    items_returned: list[ReturnItemRequest] = Field(..., description="Items being returned")
    refund_amount: float = Field(..., description="Estimated refund amount")
    summary: str = Field(..., description="Human-readable summary of the return decision")
    photo_verified: bool = Field(..., description="Whether photo verification passed")


# ---------------------------------------------------------------------------
# Executors
# ---------------------------------------------------------------------------


class ReturnIntakeExecutor(Executor):
    """Classifies the return request as full or partial and extracts order/item details."""

    agent: Agent

    def __init__(self, client: AzureAIClient, agent_suffix: str = ""):
        _id = "return-intake-agent" + agent_suffix
        self.agent = client.as_agent(
            name=_id,
            description=WORKFLOW_AGENT_DESCRIPTION,
            instructions=(
                "You are a customer-service return-intake agent for Zava Shop. "
                "Analyze the customer's message to determine:\n"
                "1. The order ID they want to return.\n"
                "2. Whether they want a FULL return (entire order) or PARTIAL return (specific items).\n"
                "3. Which items they want to return (for partial returns), INCLUDING the quantity of each item.\n"
                "   - A customer may have ordered 3 of an item but only want to return 1 or 2.\n"
                "   - If the customer says 'return one of the backpacks' and ordered 2, set quantity=1.\n"
                "   - If no quantity is mentioned, assume they want to return ALL units of that item.\n"
                "4. The reason for the return.\n\n"
                "If the customer mentions returning 'everything', 'the whole order', or 'all items', "
                "classify as a full return. Otherwise classify as partial.\n"
                "Always set the quantity field on every item in the items list."
            ),
            model_id=DEFAULT_MODEL,
            store=True,
        )
        super().__init__(id=_id)

    @handler
    async def handle(self, workflow_input: ReturnWorkflowInput, ctx: WorkflowContext[ReturnIntakeResult]) -> None:
        # Store photo data in workflow state for the PhotoVerificationExecutor
        ctx.set_state("photo_base64", workflow_input.photo_base64)
        ctx.set_state("photo_mime_type", workflow_input.photo_mime_type)

        response = await self.agent.run(
            workflow_input.message, options={"response_format": ReturnIntakeResult}
        )
        result = cast(ReturnIntakeResult, response.value)
        result.original_message = workflow_input.message
        await ctx.send_message(result)


RETURNS_POLICY_TEXT = """\
Eligible return reasons (within 30 days of delivery):
- Defective or damaged item – arrived broken, torn, or non-functional.
- Wrong item received – a different product than ordered.
- Item doesn't match description – materially different from the listing.
- Size or fit issue – clothing/footwear doesn't fit per the size guide.
- Changed mind (within 30 days) – item is unused and in original packaging.
- Duplicate order – the same order was placed twice.

Ineligible return reasons:
- Items that have been worn, washed, or used beyond initial inspection.
- Items without original tags or packaging.
- Perishable or consumable goods.
- Gift cards or store-credit vouchers.
- Items marked as Final Sale or Non-Returnable.
- Returns requested after the 30-day window.
"""


class PolicyValidationExecutor(Executor):
    """Validates the customer's return reason against the Zava Shop returns policy.

    If the reason matches an eligible category the intake result is forwarded
    downstream.  If the reason is ineligible or insufficient the executor
    short-circuits the workflow by yielding a denied ``ReturnApprovalResult``.
    """

    agent: Agent

    def __init__(self, client: AzureAIClient, agent_suffix: str = ""):
        _id = "policy-validation-agent" + agent_suffix
        self.agent = client.as_agent(
            name=_id,
            description=WORKFLOW_AGENT_DESCRIPTION,
            instructions=(
                "You are a returns-policy validation agent for Zava Shop.\n\n"
                "You will receive a customer's return reason and the store's returns policy. "
                "Determine whether the stated reason falls under an eligible category.\n\n"
                f"{RETURNS_POLICY_TEXT}\n"
                "Rules:\n"
                "- If the reason clearly matches an eligible category, set reason_valid=true "
                "  and name the matching category in policy_category.\n"
                "- If the reason is vague but could plausibly match an eligible category, "
                "  give the customer the benefit of the doubt and set reason_valid=true.\n"
                "- If the reason clearly falls under an ineligible category, or is completely "
                "  unrelated to a product return, set reason_valid=false.\n"
                "- Always provide helpful, friendly feedback in the 'feedback' field."
            ),
            model_id=DEFAULT_MODEL,
            store=True,
        )
        super().__init__(id=_id)

    @handler
    async def handle(
        self,
        intake: ReturnIntakeResult,
        ctx: WorkflowContext[ReturnIntakeResult, ReturnApprovalResult],
    ) -> None:
        prompt = (
            f"Customer wants to return order #{intake.order_id} "
            f"({intake.return_type} return).\n"
            f"Stated reason: \"{intake.reason}\"\n"
            f"Items: {[f'{i.quantity}x {i.product_name}' for i in intake.items]}\n\n"
            "Does this reason comply with the returns policy?"
        )
        response = await self.agent.run(
            prompt, options={"response_format": PolicyValidationResult}
        )
        validation = cast(PolicyValidationResult, response.value)

        if validation.reason_valid:
            # Reason is acceptable – pass the intake result downstream
            await ctx.send_message(intake)
        else:
            # Reason is ineligible – short-circuit with a denied result
            await ctx.yield_output(
                ReturnApprovalResult(
                    approved=False,
                    return_type=intake.return_type,
                    order_id=intake.order_id,
                    items_returned=intake.items,
                    refund_amount=0.0,
                    summary=validation.feedback,
                    photo_verified=False,
                )
            )


class PhotoVerificationExecutor(Executor):
    """Verifies a customer-uploaded photo for returns using a multimodal model.

    The photo should show the items being returned, ideally in or on a
    cardboard box.  Uses gpt-5-mini for multimodal image understanding.
    """

    agent: Agent

    def __init__(self, client: AzureAIClient, agent_suffix: str = ""):
        _id = "photo-verification-agent" + agent_suffix
        self.agent = client.as_agent(
            name=_id,
            description=WORKFLOW_AGENT_DESCRIPTION,
            instructions=(
                "You are a return-verification agent for Zava Shop. "
                "You will receive a photo of items being returned along with details about what "
                "the customer wants to return.\n\n"
                "Your task:\n"
                "1. Identify the items visible in the photo.\n"
                "2. Compare the visible items against the expected return items.\n"
                "3. Check that items appear to be in acceptable, unused condition.\n"
                "4. For full-order returns, verify items are in or on a cardboard box.\n"
                "5. Set 'verified' to true ONLY if:\n"
                "   - The items in the photo reasonably match the items being returned.\n"
                "   - The items appear to be in acceptable condition (not visibly "
                "worn, soiled, or damaged beyond what the customer described).\n"
                "6. List each detected item in 'items_detected'.\n"
                "7. Explain your reasoning in 'confidence_notes'.\n\n"
                "Be reasonable — items don't need perfect labels, just visual plausibility."
            ),
            model_id=MULTIMODAL_MODEL,
            store=True,
        )
        super().__init__(id=_id)

    @handler
    async def handle(
        self,
        intake: ReturnIntakeResult,
        ctx: WorkflowContext[PhotoVerificationResult],
    ) -> None:
        """Verify the return photo stored in workflow state by the intake executor."""
        # Store intake in state so the approval executor can access it
        ctx.set_state("intake_json", intake.model_dump_json())

        # Read photo data from workflow state (set by ReturnIntakeExecutor)
        photo_base64: str = ctx.get_state("photo_base64", "")
        photo_mime_type: str = ctx.get_state("photo_mime_type", "image/jpeg")

        # Build a multimodal message with the image and text context
        items_description = ", ".join(
            f"{item.quantity}x {item.product_name}" for item in intake.items
        ) or "all items in the order"

        return_kind = "full-order" if intake.return_type == "full" else "partial"
        text_prompt = (
            f"The customer wants a {return_kind} return for order #{intake.order_id}.\n"
            f"Expected items: {items_description}.\n"
            f"Reason: {intake.reason}\n\n"
            "Please verify the attached photo shows these items ready for return."
        )

        # If a photo was provided, build a multimodal content list
        if photo_base64:
            image_bytes = base64.b64decode(photo_base64)
            multimodal_content = [
                Content.from_text(text_prompt),
                Content.from_data(data=image_bytes, media_type=photo_mime_type),
            ]
            message = Message(role="user", contents=multimodal_content)
        else:
            # No photo provided — cannot verify
            result = PhotoVerificationResult(
                verified=False,
                items_detected=[],
                confidence_notes="No photo was provided. A photo of the items being returned is required.",
            )
            await ctx.send_message(result)
            return

        response = await self.agent.run(
            message, options={"response_format": PhotoVerificationResult}
        )
        result = cast(PhotoVerificationResult, response.value)
        await ctx.send_message(result)


class ReturnApprovalExecutor(Executor):
    """Processes the return approval decision and generates the final summary."""

    agent: Agent

    def __init__(self, client: AzureAIClient, agent_suffix: str = ""):
        _id = "return-approval-agent" + agent_suffix
        self.agent = client.as_agent(
            name=_id,
            description=WORKFLOW_AGENT_DESCRIPTION,
            instructions=(
                "You are a return-approval agent for Zava Shop. "
                "Based on the return request details and photo verification, "
                "generate the final return approval.\n\n"
                "Rules:\n"
                "- Approve the return only if photo verification passed (verified=true).\n"
                "- Calculate refund_amount as a reasonable estimate based on the items.\n"
                "- Provide a clear, friendly summary message for the customer.\n"
                "- If the return is denied, explain why and what the customer can do next."
            ),
            model_id=DEFAULT_MODEL,
            store=True,
        )
        super().__init__(id=_id)

    @handler
    async def handle(
        self, verification: PhotoVerificationResult, ctx: WorkflowContext[Never, ReturnApprovalResult]
    ) -> None:
        """Handle all returns after photo verification."""
        # Recover intake details from workflow state
        intake_json: str = ctx.get_state("intake_json", "")
        intake = ReturnIntakeResult.model_validate_json(intake_json) if intake_json else None

        order_info = f"order #{intake.order_id}" if intake else "unknown order"
        return_type = intake.return_type if intake else "full"
        items_list = (
            [f"{i.quantity}x {i.product_name}" for i in intake.items] if intake else []
        )

        prompt = (
            f"Process this {return_type} return for {order_info}.\n"
            f"Items to return: {items_list}\n"
            f"Photo verification result: verified={verification.verified}\n"
            f"Items detected in photo: {verification.items_detected}\n"
            f"Verification notes: {verification.confidence_notes}\n\n"
            "If photo verification passed, approve the return. Otherwise, deny it."
        )
        response = await self.agent.run(
            prompt, options={"response_format": ReturnApprovalResult}
        )
        result = cast(ReturnApprovalResult, response.value)
        result.return_type = return_type
        result.photo_verified = verification.verified
        if intake:
            result.order_id = intake.order_id
            result.items_returned = intake.items
        await ctx.yield_output(result)


# ---------------------------------------------------------------------------
# Workflow builder
# ---------------------------------------------------------------------------


def build_workflow(
    credential: AsyncTokenCredential | None = None,
    project_endpoint: str | None = None,
    agent_suffix: str = "",
) -> Workflow:
    """Build the product return workflow.

    Topology::

        ReturnIntakeExecutor
            → PolicyValidationExecutor
                ├── [reason valid] → PhotoVerificationExecutor → ReturnApprovalExecutor
                └── [reason invalid] → (yields denied ReturnApprovalResult)

    Returns:
        A compiled ``Workflow`` ready to ``.run()``.
    """
    if credential is None:
        credential = DefaultAzureCredential(
            exclude_shared_token_cache_credential=True,
            exclude_visual_studio_code_credential=True,
        )
    project_endpoint = project_endpoint or os.getenv("AZURE_AI_PROJECT_ENDPOINT")

    # Shared AI client factory
    def make_client(model: str = DEFAULT_MODEL) -> AzureAIClient:
        return AzureAIClient(
            credential=credential,
            project_endpoint=project_endpoint,
            model_deployment_name=model,
        )

    intake = ReturnIntakeExecutor(make_client(), agent_suffix=agent_suffix)
    policy = PolicyValidationExecutor(make_client(), agent_suffix=agent_suffix)
    photo_verify = PhotoVerificationExecutor(make_client(MULTIMODAL_MODEL), agent_suffix=agent_suffix)
    approval = ReturnApprovalExecutor(make_client(), agent_suffix=agent_suffix)

    workflow = (
        WorkflowBuilder(
            start_executor=intake,
            name="Product Return Workflow",
            description=(
                "Deterministic workflow for processing customer product returns. "
                "Returns are validated against the store policy. "
                "All returns require photo verification of the items being returned."
            ),
        )
        .add_edge(intake, policy)
        .add_edge(policy, photo_verify)
        .add_edge(photo_verify, approval)
        .build()
    )

    return workflow

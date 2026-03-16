"""Tests for the Product Return Workflow.

These tests validate:
- Policy validation (eligible and ineligible return reasons)
- Photo verification for all return types
- Partial return path (intake -> policy -> photo verification -> approval)
- Full return path (intake -> policy -> photo verification -> approval)
- Workflow graph structure
- Data model serialisation round-trips
"""

import base64
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from azure.identity.aio import DefaultAzureCredential

from zava_shop_agents.returns import (
    PolicyValidationResult,
    ReturnApprovalResult,
    ReturnIntakeResult,
    ReturnItemRequest,
    ReturnWorkflowInput,
    build_workflow,
)

TEST_IMAGES_DIR = Path(__file__).parent / "data" / "return_images"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def azure_credential():
    return DefaultAzureCredential()


def load_test_image(filename: str) -> str:
    """Load a test image and return its base64 encoding."""
    image_path = TEST_IMAGES_DIR / filename
    if not image_path.exists():
        pytest.skip(f"Test image not found: {image_path}")
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


# ---------------------------------------------------------------------------
# Unit-level tests (no AI endpoint required)
# ---------------------------------------------------------------------------


class TestDataModels:
    """Validate data model construction and serialisation."""

    def test_return_workflow_input_defaults(self):
        inp = ReturnWorkflowInput(message="I want to return order #1")
        assert inp.photo_base64 == ""
        assert inp.photo_mime_type == "image/jpeg"

    def test_return_workflow_input_with_photo(self):
        inp = ReturnWorkflowInput(
            message="Return everything",
            photo_base64="abc123==",
            photo_mime_type="image/png",
        )
        assert inp.photo_base64 == "abc123=="
        assert inp.photo_mime_type == "image/png"

    def test_return_intake_result_round_trip(self):
        result = ReturnIntakeResult(
            order_id=42,
            return_type="partial",
            items=[ReturnItemRequest(product_name="T-Shirt", sku="", quantity=2)],
            reason="Too small",
            original_message="I want to return these",
        )
        data = result.model_dump()
        restored = ReturnIntakeResult(**data)
        assert restored.order_id == 42
        assert restored.return_type == "partial"
        assert len(restored.items) == 1
        assert restored.items[0].product_name == "T-Shirt"

    def test_return_approval_result_defaults(self):
        result = ReturnApprovalResult(
            approved=True,
            return_type="full",
            order_id=99,
            items_returned=[],
            refund_amount=0.0,
            summary="",
            photo_verified=False,
        )
        assert result.refund_amount == 0.0
        assert result.photo_verified is False
        assert result.summary == ""

    def test_policy_validation_result_valid(self):
        result = PolicyValidationResult(
            reason_valid=True,
            policy_category="Defective or damaged item",
            feedback="Your reason is covered by our returns policy.",
        )
        assert result.reason_valid is True
        assert result.policy_category == "Defective or damaged item"

    def test_policy_validation_result_invalid(self):
        result = PolicyValidationResult(
            reason_valid=False,
            policy_category="none",
            feedback="We're unable to accept returns for this reason.",
        )
        assert result.reason_valid is False
        assert result.policy_category == "none"


class TestWorkflowStructure:
    """Validate that build_workflow produces a well-formed graph.

    Uses a mock credential / endpoint – only checks the graph, not AI calls.
    """

    def test_workflow_has_correct_executors(self):
        cred = MagicMock(spec=DefaultAzureCredential)
        workflow = build_workflow(
            credential=cred,
            project_endpoint="https://fake.endpoint.test/",
            agent_suffix="-struct",
        )
        executor_ids = set(workflow.executors.keys())
        assert "return-intake-agent-struct" in executor_ids
        assert "policy-validation-agent-struct" in executor_ids
        assert "photo-verification-agent-struct" in executor_ids
        assert "return-approval-agent-struct" in executor_ids

    def test_workflow_input_type_is_workflow_input(self):
        cred = MagicMock(spec=DefaultAzureCredential)
        workflow = build_workflow(
            credential=cred,
            project_endpoint="https://fake.endpoint.test/",
            agent_suffix="-types",
        )
        # The start executor should accept ReturnWorkflowInput
        assert ReturnWorkflowInput in workflow.input_types


# ---------------------------------------------------------------------------
# Integration tests (require AZURE_AI_PROJECT_ENDPOINT)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
    reason="AZURE_AI_PROJECT_ENDPOINT is not configured for integration tests",
)
@pytest.mark.asyncio
async def test_partial_return_path(azure_credential):
    """Partial return with a photo should be approved.

    All returns now go through: intake -> policy -> photo verify -> approval.
    """
    workflow = build_workflow(credential=azure_credential, agent_suffix="-test")

    workflow_input = ReturnWorkflowInput(
        message="I want to return the Brown Leather Shoes from order #101. They don't fit.",
        photo_base64=load_test_image("brown shoes.jpg"),
        photo_mime_type="image/jpeg",
    )
    result = await workflow.run(workflow_input)

    # All returns go through 4 executors: intake + policy + photo verify + approval
    executor_completions = [
        event for event in result if getattr(event, "type", None) == "executor_completed"
    ]
    assert len(executor_completions) == 4, (
        f"Expected 4 executor completions for partial return, got {len(executor_completions)}"
    )

    outputs = result.get_outputs()
    assert len(outputs) == 1

    approval = outputs[0]
    assert isinstance(approval, ReturnApprovalResult)
    assert approval.return_type == "partial"
    assert approval.approved is True
    assert approval.summary  # Should have a summary message


@pytest.mark.skipif(
    not os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
    reason="AZURE_AI_PROJECT_ENDPOINT is not configured for integration tests",
)
@pytest.mark.asyncio
async def test_full_return_with_valid_photo(azure_credential):
    """Full return with a valid photo (belt in a box) should be approved."""
    workflow = build_workflow(credential=azure_credential, agent_suffix="-test")

    workflow_input = ReturnWorkflowInput(
        message="I want to return my entire order #202. I received the wrong belt.",
        photo_base64=load_test_image("belt in box.jpg"),
        photo_mime_type="image/jpeg",
    )
    result = await workflow.run(workflow_input)

    # Full return goes through 4 executors: intake + policy + photo verify + approval
    executor_completions = [
        event for event in result if getattr(event, "type", None) == "executor_completed"
    ]
    assert len(executor_completions) == 4, (
        f"Expected 4 executor completions for full return, got {len(executor_completions)}"
    )

    outputs = result.get_outputs()
    assert len(outputs) == 1

    approval = outputs[0]
    assert isinstance(approval, ReturnApprovalResult)
    assert approval.return_type == "full"
    assert approval.photo_verified is True
    assert approval.approved is True
    assert approval.summary


@pytest.mark.skipif(
    not os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
    reason="AZURE_AI_PROJECT_ENDPOINT is not configured for integration tests",
)
@pytest.mark.asyncio
async def test_full_return_without_photo(azure_credential):
    """Full return without a photo should be denied (photo_verified=False)."""
    workflow = build_workflow(credential=azure_credential, agent_suffix="-test")

    workflow_input = ReturnWorkflowInput(
        message="I want to return everything from order #303.",
        photo_base64="",  # No photo
    )
    result = await workflow.run(workflow_input)

    # Full return routes through 4 executors: intake + policy + photo verify + approval
    executor_completions = [
        event for event in result if getattr(event, "type", None) == "executor_completed"
    ]
    assert len(executor_completions) == 4

    outputs = result.get_outputs()
    assert len(outputs) == 1

    approval = outputs[0]
    assert isinstance(approval, ReturnApprovalResult)
    assert approval.return_type == "full"
    # Without a photo, should not be verified/approved
    assert approval.photo_verified is False
    assert approval.approved is False


@pytest.mark.skipif(
    not os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
    reason="AZURE_AI_PROJECT_ENDPOINT is not configured for integration tests",
)
@pytest.mark.asyncio
async def test_full_return_with_invalid_photo(azure_credential):
    """Full return with items NOT in a box should be denied."""
    workflow = build_workflow(credential=azure_credential, agent_suffix="-test")

    workflow_input = ReturnWorkflowInput(
        message="I'd like to return all of order #404 please.",
        photo_base64=load_test_image("invalid_no_box.jpg"),
        photo_mime_type="image/jpeg",
    )
    result = await workflow.run(workflow_input)

    executor_completions = [
        event for event in result if getattr(event, "type", None) == "executor_completed"
    ]
    assert len(executor_completions) == 4

    outputs = result.get_outputs()
    assert len(outputs) == 1

    approval = outputs[0]
    assert isinstance(approval, ReturnApprovalResult)
    assert approval.return_type == "full"
    # Photo should fail verification (no box visible)
    assert approval.photo_verified is False
    assert approval.approved is False


@pytest.mark.skipif(
    not os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
    reason="AZURE_AI_PROJECT_ENDPOINT is not configured for integration tests",
)
@pytest.mark.asyncio
async def test_multiple_items_partial_return(azure_credential):
    """Partial return requesting multiple specific items with photo should be approved."""
    workflow = build_workflow(credential=azure_credential, agent_suffix="-test")

    workflow_input = ReturnWorkflowInput(
        message=(
            "I'd like to return the Brown Shoes from order #505. "
            "They don't match the photos on the website."
        ),
        photo_base64=load_test_image("brown shoes.jpg"),
        photo_mime_type="image/jpeg",
    )
    result = await workflow.run(workflow_input)

    outputs = result.get_outputs()
    assert len(outputs) == 1

    approval = outputs[0]
    assert isinstance(approval, ReturnApprovalResult)
    assert approval.return_type == "partial"
    assert approval.approved is True
    assert len(approval.items_returned) >= 1  # At least one item extracted


@pytest.mark.skipif(
    not os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
    reason="AZURE_AI_PROJECT_ENDPOINT is not configured for integration tests",
)
@pytest.mark.asyncio
async def test_partial_quantity_return(azure_credential):
    """Customer ordered 2 backpacks but only wants to return 1.

    The intake agent should extract quantity=1 for the backpack.
    """
    workflow = build_workflow(credential=azure_credential, agent_suffix="-test")

    workflow_input = ReturnWorkflowInput(
        message=(
            "I ordered 2 black boots from order #550 but only want to return 1 of them. "
            "One pair doesn't fit, so I'd like to keep the other."
        ),
        photo_base64=load_test_image("black boots.jpg"),
        photo_mime_type="image/jpeg",
    )
    result = await workflow.run(workflow_input)

    outputs = result.get_outputs()
    assert len(outputs) == 1

    approval = outputs[0]
    assert isinstance(approval, ReturnApprovalResult)
    assert approval.return_type == "partial"
    assert approval.approved is True
    # The agent should have extracted quantity=1 for the boots
    assert len(approval.items_returned) >= 1
    boot_item = approval.items_returned[0]
    assert boot_item.quantity == 1, (
        f"Expected quantity 1 for partial qty return, got {boot_item.quantity}"
    )


@pytest.mark.skipif(
    not os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
    reason="AZURE_AI_PROJECT_ENDPOINT is not configured for integration tests",
)
@pytest.mark.asyncio
async def test_invalid_reason_denied_by_policy(azure_credential):
    """A return with an ineligible reason should be denied by the policy validator."""
    workflow = build_workflow(credential=azure_credential, agent_suffix="-test")

    workflow_input = ReturnWorkflowInput(
        message=(
            "I want to return the running shoes from order #606. "
            "I've worn them for three months jogging outdoors but now "
            "I want a different colour."
        ),
    )
    result = await workflow.run(workflow_input)

    outputs = result.get_outputs()
    assert len(outputs) == 1

    approval = outputs[0]
    assert isinstance(approval, ReturnApprovalResult)
    assert approval.approved is False  # Policy should reject worn items
    assert approval.summary  # Feedback explaining why it was denied


@pytest.mark.skipif(
    not os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
    reason="AZURE_AI_PROJECT_ENDPOINT is not configured for integration tests",
)
@pytest.mark.asyncio
async def test_full_return_black_boots(azure_credential):
    """Full return of black boots with a valid photo should be approved."""
    workflow = build_workflow(credential=azure_credential, agent_suffix="-test")

    workflow_input = ReturnWorkflowInput(
        message="I want to return my entire order #707. The black boots don't fit.",
        photo_base64=load_test_image("black boots.jpg"),
        photo_mime_type="image/jpeg",
    )
    result = await workflow.run(workflow_input)

    outputs = result.get_outputs()
    assert len(outputs) == 1

    approval = outputs[0]
    assert isinstance(approval, ReturnApprovalResult)
    assert approval.return_type == "full"
    assert approval.approved is True
    assert approval.summary


@pytest.mark.skipif(
    not os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
    reason="AZURE_AI_PROJECT_ENDPOINT is not configured for integration tests",
)
@pytest.mark.asyncio
async def test_full_return_brown_shoes(azure_credential):
    """Full return of brown shoes with a valid photo should be approved."""
    workflow = build_workflow(credential=azure_credential, agent_suffix="-test")

    workflow_input = ReturnWorkflowInput(
        message="I want to return my entire order #808. The brown shoes don't match the description.",
        photo_base64=load_test_image("brown shoes.jpg"),
        photo_mime_type="image/jpeg",
    )
    result = await workflow.run(workflow_input)

    outputs = result.get_outputs()
    assert len(outputs) == 1

    approval = outputs[0]
    assert isinstance(approval, ReturnApprovalResult)
    assert approval.return_type == "full"
    assert approval.approved is True
    assert approval.summary


@pytest.mark.skipif(
    not os.getenv("AZURE_AI_PROJECT_ENDPOINT"),
    reason="AZURE_AI_PROJECT_ENDPOINT is not configured for integration tests",
)
@pytest.mark.asyncio
async def test_dirty_shoes_rejected(azure_credential):
    """Full return with visibly used/soiled shoes should be denied by policy."""
    workflow = build_workflow(credential=azure_credential, agent_suffix="-test")

    workflow_input = ReturnWorkflowInput(
        message=(
            "I want to return my entire order #909. "
            "The shoes are dirty and scuffed after I wore them outside for a few weeks."
        ),
        photo_base64=load_test_image("dirty shoes.jpg"),
        photo_mime_type="image/jpeg",
    )
    result = await workflow.run(workflow_input)

    outputs = result.get_outputs()
    assert len(outputs) == 1

    approval = outputs[0]
    assert isinstance(approval, ReturnApprovalResult)
    assert approval.approved is False  # Used/soiled items are ineligible per policy
    assert approval.summary  # Should explain why the return was denied

"""
Returns router – handles product-return requests from customers.

Exposes a POST /api/returns endpoint that:
1. Accepts a return request (order ID, items, optional photo).
2. Runs the deterministic return workflow (Microsoft Agent Framework).
3. Streams workflow events back to the caller via SSE.
"""

import base64
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from zava_shop_api.models import TokenData
from zava_shop_api.openid_auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/returns", tags=["returns"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ReturnItemInput(BaseModel):
    """A single item in a partial-return request."""
    product_name: str = Field(..., description="Product name")
    sku: str = Field(default="", description="Product SKU")
    quantity: int = Field(default=1, ge=1, description="Quantity to return")


class ReturnRequest(BaseModel):
    """Body for the return-request endpoint."""
    order_id: int = Field(..., description="Order ID to return")
    return_type: str = Field(..., description="'full' or 'partial'")
    items: list[ReturnItemInput] = Field(default_factory=list, description="Items for partial return")
    reason: str = Field(default="", description="Reason for the return")


class ReturnResponse(BaseModel):
    """Response from the return workflow."""
    approved: bool
    return_type: str
    order_id: int
    items_returned: list[ReturnItemInput] = []
    refund_amount: float = 0.0
    summary: str = ""
    photo_verified: bool = False


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("", response_model=ReturnResponse)
async def submit_return(
    order_id: int = Form(...),
    return_type: str = Form(...),
    reason: str = Form(""),
    items_json: str = Form("[]"),
    photo: Optional[UploadFile] = File(None),
    current_user: TokenData = Depends(get_current_user),
):
    """
    Submit a product-return request.

    A photo of the items being returned is required for all return types.
    The return is processed by the Product Return Workflow (Microsoft Agent Framework).
    """
    import json

    if current_user.user_role != "customer":
        raise HTTPException(status_code=403, detail="Only customers can submit returns")

    if return_type not in ("full", "partial"):
        raise HTTPException(status_code=400, detail="return_type must be 'full' or 'partial'")

    # Parse items JSON
    try:
        items_raw = json.loads(items_json)
        items = [ReturnItemInput(**i) for i in items_raw]
    except Exception:
        items = []

    # Photo is required for all returns
    photo_base64 = ""
    photo_mime = "image/jpeg"
    if photo is None:
        raise HTTPException(
            status_code=400,
            detail="A photo of the items being returned is required.",
        )
    photo_bytes = await photo.read()
    photo_base64 = base64.b64encode(photo_bytes).decode("utf-8")
    photo_mime = photo.content_type or "image/jpeg"

    # Build and run the return workflow
    try:
        from zava_shop_agents.returns import (
            ReturnApprovalResult,
            ReturnWorkflowInput,
            build_workflow,
        )

        workflow = build_workflow()

        # Compose the user message for the intake executor
        if return_type == "full":
            user_message = (
                f"I want to return my entire order #{order_id}. "
                f"Reason: {reason or 'No reason provided'}. "
                "I am returning all items."
            )
        else:
            items_desc = ", ".join(f"{i.quantity}x {i.product_name}" for i in items)
            user_message = (
                f"I want to return some items from order #{order_id}: {items_desc}. "
                f"Reason: {reason or 'No reason provided'}."
            )

        # Run the workflow with structured input including photo data
        workflow_input = ReturnWorkflowInput(
            message=user_message,
            photo_base64=photo_base64,
            photo_mime_type=photo_mime,
        )
        result_events = await workflow.run(workflow_input)

        # Extract final output
        workflow_outputs = result_events.get_outputs()

        if workflow_outputs:
            approval: ReturnApprovalResult = workflow_outputs[0]
            return ReturnResponse(
                approved=approval.approved,
                return_type=approval.return_type,
                order_id=approval.order_id,
                items_returned=[
                    ReturnItemInput(
                        product_name=i.product_name,
                        sku=i.sku,
                        quantity=i.quantity,
                    )
                    for i in approval.items_returned
                ],
                refund_amount=approval.refund_amount,
                summary=approval.summary,
                photo_verified=approval.photo_verified,
            )
        else:
            # Workflow completed without a structured output – fallback
            return ReturnResponse(
                approved=False,
                return_type=return_type,
                order_id=order_id,
                summary="The return workflow did not produce a result. Please try again or contact support.",
            )

    except ImportError:
        logger.warning("Return agent workflow not available — using fallback logic")
        # Fallback when agent framework is not configured
        return ReturnResponse(
            approved=True,
            return_type=return_type,
            order_id=order_id,
            items_returned=items,
            refund_amount=0.0,
            summary=(
                f"Return request received for order #{order_id} ({return_type} return). "
                "A support agent will review your request and process the refund."
            ),
            photo_verified=return_type == "full" and photo is not None,
        )
    except Exception as e:
        logger.error(f"Return workflow error: {e}", exc_info=True)
        return JSONResponse(
            content={"error": f"Failed to process return: {str(e)}"},
            status_code=500,
        )

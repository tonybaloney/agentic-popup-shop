# Product Return Workflow

## Overview

The product return workflow allows authenticated customers to return products through a multi-step, AI-verified process. It supports both **full-order returns** (all items) and **partial returns** (specific items).

The workflow is built as a deterministic pipeline using **Microsoft Agent Framework** with `WorkflowBuilder`, `Executor` nodes, and conditional branching.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Customer Initiates Return                     │
│                                                                  │
│  Via Chat ("I want to return my order")                          │
│  OR                                                              │
│  Via Dashboard (click Return button on order card)               │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
          ┌────────────────────────────────┐
          │    ReturnIntakeExecutor         │
          │    (gpt-5-mini)                │
          │                                │
          │  • Classifies: full / partial  │
          │  • Extracts order ID & items   │
          │  • Captures return reason      │
          └───────┬──────────────┬─────────┘
                  │              │
          ┌───────┘              └──────┐
          │ full return         partial │
          ▼                        return│
  ┌───────────────────────┐        │
  │ PhotoVerificationExec │        │
  │ (gpt-5.3-chat)        │        │
  │                       │        │
  │ • Multimodal model    │        │
  │ • Verifies photo shows│        │
  │   items in cardboard  │        │
  │   box                 │        │
  │ • Lists detected items│        │
  └──────────┬────────────┘        │
             │                     │
             ▼                     ▼
  ┌────────────────────────────────────┐
  │     ReturnApprovalExecutor         │
  │     (gpt-5-mini)                   │
  │                                    │
  │  • Full: approved if photo passed  │
  │  • Partial: always approved        │
  │  • Estimates refund amount         │
  │  • Generates customer summary      │
  └────────────────────────────────────┘
                    │
                    ▼
           Return result sent
           to customer via chat
           or API response
```

## Entry Points

### 1. Chat Agent (Conversational)

When a customer says something like _"I want to return a product"_ or _"Can I return my last order?"_ in the chat:

1. The **Zava customer chat agent** detects return intent.
2. It calls `get_orders()` to retrieve the customer's orders.
3. It calls `initiate_return(order_id)` to start the return flow.
4. A **return widget** is displayed in the chat with order details and instructions.
5. The customer clicks the **Return** button on their dashboard to open the return form.

### 2. Dashboard (Direct)

Each order card on the **Customer Dashboard** has a **Return** button that opens the return form modal directly.

## Frontend Return Form

The `ReturnForm.vue` component is a 3-step modal:

| Step | Name | Description |
|------|------|-------------|
| 1 | **Select Items** | Choose full or partial return; for partial, select specific items. Enter a reason. |
| 2 | **Upload Photo / Confirm** | Full returns: upload a photo of items in the box. Partial returns: review and confirm. |
| 3 | **Result** | Shows approved/denied status, refund amount, and summary. |

### Photo Requirements (Full Returns)

- Must show items placed **inside or on top of a cardboard box**
- Image formats: JPG, PNG (up to 10MB)
- Drag-and-drop or click-to-upload
- AI verification uses **gpt-5.3-chat** (multimodal)

## API Endpoint

```
POST /api/returns
Content-Type: multipart/form-data
Authorization: Bearer <token>

Form fields:
  order_id     (int)    – Required. The order to return.
  return_type  (string) – Required. "full" or "partial".
  reason       (string) – Optional. Reason for return.
  items_json   (string) – JSON array of items for partial returns.
  photo        (file)   – Required for full returns. Photo of items in box.
```

**Response:**
```json
{
  "approved": true,
  "return_type": "full",
  "order_id": 42,
  "items_returned": [
    {"product_name": "Classic Cotton T-Shirt", "sku": "SKU001", "quantity": 2}
  ],
  "refund_amount": 49.98,
  "summary": "Your return for order #42 has been approved. ...",
  "photo_verified": true
}
```

## Agent Workflow Details

### Models Used

| Executor | Model | Purpose |
|----------|-------|---------|
| `ReturnIntakeExecutor` | `gpt-5-mini` | Text classification and entity extraction |
| `PhotoVerificationExecutor` | `gpt-5.3-chat` | Multimodal image + text verification |
| `ReturnApprovalExecutor` | `gpt-5-mini` | Decision logic and summary generation |

### Branching Logic

The workflow uses `Case`/`Default` branching (same pattern as the supplier review workflow):

```python
WorkflowBuilder(start_executor=intake)
    .add_switch_case_edge_group(
        intake,
        [
            Case(condition=is_full_return(), target=photo_verify),
            Default(target=approval),
        ],
    )
    .add_edge(photo_verify, approval)
    .build()
```

- **Full return** → `PhotoVerificationExecutor` → `ReturnApprovalExecutor`
- **Partial return** → `ReturnApprovalExecutor` (directly)

### Photo Verification Logic

The `PhotoVerificationExecutor` checks:
1. A cardboard box is clearly visible in the photo
2. Items in the photo reasonably match the order items
3. Sets `verified=true` only if both conditions are met
4. Lists each detected item and explains its reasoning

## Test Images

Test images are in `app/agents/tests/data/return_images/`:

| File | Description | Expected Result |
|------|-------------|-----------------|
| `valid_full_return_box.jpg` | 3 items in a cardboard box | `verified: true` |
| `valid_partial_return_box.jpg` | 1 item in a cardboard box | `verified: true` |
| `invalid_no_box.jpg` | Items scattered, no box | `verified: false` |
| `valid_clothing_return.jpg` | 4 clothing items in a box | `verified: true` |
| `invalid_empty_box.jpg` | Empty cardboard box | `verified: false` |

## File Locations

| Component | Path |
|-----------|------|
| Return Agent Workflow | `app/agents/src/zava_shop_agents/returns.py` |
| Return API Router | `app/api/src/zava_shop_api/routers/returns.py` |
| Return Form (Frontend) | `frontend/src/components/ReturnForm.vue` |
| Chat Integration | `app/api/src/zava_shop_api/routers/chatkit.py` |
| Agent Tests | `app/agents/tests/test_returns.py` |
| Test Images | `app/agents/tests/data/return_images/` |

## Running Tests

```bash
cd app/agents
uv run --prerelease=allow pytest tests/test_returns.py -v
```

> **Note:** Integration tests that call Azure AI models require `AZURE_AI_PROJECT_ENDPOINT` to be set.

# KAIRO: Linear App Integration & Webhooks Guide

> **Domain:** Integrations & Connectors  
> **Document ID:** KAIRO-INT-LINEAR  
> **Target:** Linear App Ingress, Webhook Verification & Issue Synchronization

---

## 1. Linear Webhook Configuration

1. In Linear, go to **Settings** $\rightarrow$ **API** $\rightarrow$ **Webhooks** $\rightarrow$ **New Webhook**.
2. **Settings:**
   * **URL (Default Multi-Tenant):** `https://<your-domain>/api/v1/webhooks/linear`
   * **URL (Tenant Scoped):** `https://<your-domain>/api/v1/webhooks/linear/{organization_id}`
   * **Resource Types:** Issues, Comments, Projects, Issue transitions.
3. Click **Create Webhook**.

---

## 2. Ingress Headers & Delivery Protocol

Linear webhooks send the following custom HTTP headers:
* `Linear-Event`: Name of the entity type (e.g. `Issue`, `Comment`, `Project`).
* `Linear-Delivery`: Unique UUID for event deduplication and delivery tracking.

---

## 3. Webhook Payload Normalization

KAIRO's Celery task `workers.tasks.ingest.process_linear_webhook` normalizes Linear issues into the unified `WorkItem` schema:

```json
{
  "action": "update",
  "type": "Issue",
  "data": {
    "id": "c1f7a29e-4b11-4033-9bc2-89b6a12f389a",
    "identifier": "ENG-104",
    "number": 104,
    "title": "Migrate payment webhook handler to idempotency keys",
    "description": "Ensure double-charging does not occur on network timeouts.",
    "state": {
      "name": "Done"
    },
    "assignee": {
      "id": "usr_lin_8821",
      "name": "Rahul Sharma",
      "email": "rahul@snapmeet.com"
    }
  }
}
```

### State Mapping Table
| Linear State Name | Normalized KAIRO `WorkItemStatus` |
| :--- | :--- |
| `Done`, `Completed` | `WorkItemStatus.DONE` |
| `In Review`, `Review` | `WorkItemStatus.IN_REVIEW` |
| `In Progress` | `WorkItemStatus.IN_PROGRESS` |
| `Canceled`, `Cancelled` | `WorkItemStatus.CLOSED` |
| `Todo`, `Backlog`, other | `WorkItemStatus.TO_DO` |

---

## 4. Anomaly Evaluation & Handoff Integration

Once normalized:
1. Linear task status is compared against GitHub/GitLab PR states for rule `HW-03` (Declared vs Observed State Mismatch).
2. Developer assignments trigger transition handoff preparation for incoming team members.

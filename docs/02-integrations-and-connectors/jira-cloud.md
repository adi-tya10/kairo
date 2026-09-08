# KAIRO: Jira Cloud Integration & Webhooks Guide

> **Domain:** Integrations & Connectors  
> **Document ID:** KAIRO-INT-JIRA  
> **Target:** Atlassian Jira Cloud REST API & Webhook Subsystem

---

## 1. Integration Methods

### Method A: API Token (Local Dev / Prototyping)
1. Sign up for a free Jira Cloud site at [atlassian.com](https://www.atlassian.com/software/jira).
2. Generate an API token at [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens).
3. Set credentials in `.env`:
   ```env
   JIRA_BASE_URL="https://your-domain.atlassian.net"
   JIRA_USER_EMAIL="your-email@example.com"
   JIRA_API_TOKEN="ATATT3xFfGF0..."
   ```

### Method B: Production Webhook Subscription
1. Navigate to **Jira Settings** $\rightarrow$ **System** $\rightarrow$ **Webhooks** (`/plugins/servlet/webhooks`).
2. Click **Create a WebHook**:
   * **URL (Global):** `https://<your-domain>/api/v1/webhooks/jira`
   * **URL (Tenant Scoped):** `https://<your-domain>/api/v1/webhooks/jira/{organization_id}`
   * **Events:**
     * Issue: `created`, `updated`, `deleted`
     * JQL Filter (optional): `project IN ("PAY", "BILL", "CORE")`
3. Click **Save**.

---

## 2. Webhook Event Payload & Assignee Transition Detection

KAIRO processes `jira:issue_updated` events to track assignee changes (handoff triggers) and declared status transitions:

```json
{
  "timestamp": 1771994400000,
  "webhookEvent": "jira:issue_updated",
  "issue": {
    "id": "10042",
    "key": "BILL-204",
    "fields": {
      "summary": "Implement Idempotent Refund Webhook",
      "status": { "name": "In Progress" },
      "assignee": {
        "accountId": "jira-user-rahul",
        "displayName": "Rahul Sharma",
        "emailAddress": "rahul@snapmeet.com"
      },
      "project": { "id": "10001", "key": "BILL", "name": "Billing" }
    }
  },
  "changelog": {
    "items": [
      {
        "field": "assignee",
        "from": "jira-user-rahul",
        "fromString": "Rahul Sharma",
        "to": "jira-user-aman",
        "toString": "Aman Verma"
      }
    ]
  }
}
```

* **Relational Normalization:** Stored in `work_items` with `source = 'jira'`, `item_type = 'issue'`.
* **Transition Trigger:** When `changelog` indicates an `assignee` change, KAIRO initiates handoff preparation for the successor engineer.

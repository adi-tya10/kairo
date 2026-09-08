# KAIRO: GitLab Integration & Webhooks Guide

> **Domain:** Integrations & Connectors  
> **Document ID:** KAIRO-INT-GITLAB  
> **Target:** GitLab Webhook Ingress, Merge Requests & Pipeline Ingestion

---

## 1. GitLab Webhook Configuration

1. In GitLab, navigate to your Project or Group: **Settings** $\rightarrow$ **Webhooks**.
2. **Settings:**
   * **URL (Default Multi-Tenant):** `https://<your-domain>/api/v1/webhooks/gitlab`
   * **URL (Tenant Scoped):** `https://<your-domain>/api/v1/webhooks/gitlab/{organization_id}`
   * **Secret Token:** Shared secret token validated via `X-Gitlab-Token` header.
   * **Trigger Events:**
     * `Merge request events`
     * `Push events`
     * `Pipeline events`
3. Click **Add webhook**.

---

## 2. Ingress Headers & Verification

* `X-Gitlab-Event`: Event descriptor (e.g. `Merge Request Hook`, `Pipeline Hook`, `Push Hook`).
* `X-Gitlab-Token`: Token string matching configured organization secret.

---

## 3. Webhook Normalization & Structural Linking

KAIRO's Celery task `workers.tasks.ingest.process_gitlab_webhook` parses GitLab event payloads:

```json
{
  "object_kind": "merge_request",
  "project": {
    "name": "billing-service",
    "path_with_namespace": "snapmeet/billing-service"
  },
  "object_attributes": {
    "id": 9923,
    "iid": 12,
    "title": "Resolve BILL-204 timeout retry handling",
    "description": "Fixes BILL-204 by adding exponential backoff retry logic.",
    "source_branch": "feat/BILL-204-retry-queue",
    "target_branch": "main",
    "state": "opened"
  }
}
```

### 4-Tier Structural Key Extraction
The webhook parser scans:
1. `object_attributes.title`
2. `object_attributes.description`
3. `object_attributes.source_branch`

Extracted issue keys (e.g., `BILL-204`) link the Merge Request to the corresponding Jira/Linear `WorkItem` to fuel deterministic anomaly detection (`HW-01` through `HW-05`).

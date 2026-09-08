# KAIRO: Webhook Ingress Contracts & Verification

> **Domain:** API & Developer Contracts  
> **Document ID:** KAIRO-API-WEBHOOKS  
> **Standard:** Cryptographic Ingress with Non-Blocking Celery Queues

---

## 1. Webhook Endpoints Summary

| Endpoint | Source System | Signature / Token Header | Celery Handler Task |
| :--- | :--- | :--- | :--- |
| `POST /api/v1/webhooks/github[/{org_id}]` | GitHub App | `X-Hub-Signature-256`, `X-GitHub-Delivery`, `X-GitHub-Event` | `workers.tasks.ingest.process_github_webhook` |
| `POST /api/v1/webhooks/jira[/{org_id}]` | Jira Cloud | `X-Atlassian-Webhook-Identifier` | `workers.tasks.ingest.process_jira_webhook` |
| `POST /api/v1/webhooks/linear[/{org_id}]` | Linear App | `Linear-Event`, `Linear-Delivery` | `workers.tasks.ingest.process_linear_webhook` |
| `POST /api/v1/webhooks/gitlab[/{org_id}]` | GitLab | `X-Gitlab-Event`, `X-Gitlab-Token` | `workers.tasks.ingest.process_gitlab_webhook` |

---

## 2. Ingress Idempotency Architecture

```mermaid
flowchart LR
    REQ["Incoming Webhook Event"] --> SIG["Verify HMAC Signature / Token"]
    SIG --> HASH["Compute SHA-256(EventID + Body)"]
    HASH --> REDIS{"Exists in Redis?\n(TTL = 24h)"}
    REDIS -- Yes --> ACK_DUP["Return 200 OK (Discard Duplicate)"]
    REDIS -- No --> SET_CACHE["Set Key in Redis"]
    SET_CACHE --> ENQUEUE["Enqueue Celery Job"]
    ENQUEUE --> ACK["Return 202 Accepted"]
```

All webhook payloads return `202 Accepted` immediately upon cryptographic validation and are processed asynchronously by Celery workers to maintain sub-20ms ingress latency.

---

## 3. Cryptographic Rejection Contracts (Negative Paths)

Every webhook ingress endpoint enforces fail-closed cryptographic validation before reading or parsing payload contents:

* **Missing Signature / Token:** Returns `HTTP 401 Unauthorized` (`detail: "Unauthorized webhook: Missing <header>"`).
* **Invalid / Tampered Signature:** Returns `HTTP 401 Unauthorized` (`detail: "Unauthorized webhook: <Provider> HMAC signature verification failed"`).
* **Timing Attack Prevention:** All signature and token comparisons use constant-time `hmac.compare_digest`.

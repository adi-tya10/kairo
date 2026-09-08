# KAIRO: REST API Reference & Endpoint Specification

> **Domain:** API & Developer Contracts  
> **Document ID:** KAIRO-API-REST  
> **Specification:** OpenAPI 3.1.0 Compliant  
> **Base URL:** `http://localhost:8000/api/v1` (Local) / `https://api.kairo.dev/api/v1` (Production)

---

## 1. Authentication & Tenant Identity (`/auth`)

### 1.1 Register Tenant Organization
* **Path:** `POST /api/v1/auth/register`
* **Status Code:** `201 Created`
* **Request:**
  ```json
  {
    "company_name": "Acme Corp",
    "admin_email": "admin@acme.com",
    "password": "SecurePassword2026!",
    "plan_tier": "ENTERPRISE"
  }
  ```
* **Response:**
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "user_id": "usr_acme-corp_admin",
    "email": "admin@acme.com",
    "name": "Acme Corp Admin",
    "organization_id": "acme-corp",
    "company_name": "Acme Corp",
    "is_org_admin": true,
    "allowed_repos": ["acme-corp/primary-repo"]
  }
  ```

### 1.2 Login User
* **Path:** `POST /api/v1/auth/login`
* **Status Code:** `200 OK`
* **Request:**
  ```json
  {
    "email": "admin@snapmeet.com",
    "password": "KairoEnterprise2026!"
  }
  ```
* **Response:** Returns JWT `access_token` and user permission profile.

### 1.3 Get Current User Profile
* **Path:** `GET /api/v1/auth/me`
* **Header:** `Authorization: Bearer <token>`
* **Status Code:** `200 OK`
* **Response:**
  ```json
  {
    "user_id": "usr_snapmeet_admin",
    "email": "admin@snapmeet.com",
    "name": "SnapMeet Admin",
    "organization_id": "snapmeet",
    "company_name": "SnapMeet Inc.",
    "is_org_admin": true,
    "allowed_repos": ["snapmeet/billing-service", "snapmeet/auth-service"]
  }
  ```

---

## 2. Health & Liveness (`/health`)

* **Path:** `GET /api/v1/health`
* **Status Code:** `200 OK`
* **Response:**
  ```json
  {
    "status": "healthy",
    "service": "kairo-api",
    "version": "0.1.0"
  }
  ```

---

## 3. Pre-Retrieval ACL Context Gate (`/context`)

* **Path:** `GET /api/v1/context/work-items/{external_id}?repo_id={repo_id}`
* **Header:** `Authorization: Bearer <token>`
* **Status Code:** `200 OK` (or `403 Forbidden` if repository is unassigned)
* **Response:**
  ```json
  {
    "status": "authorized",
    "external_id": "BILL-204",
    "repo_id": "snapmeet/billing-service",
    "user_id": "usr_aman",
    "access_granted": true
  }
  ```

---

## 4. Grounded Handoff Package Generation (`/handoff`)

* **Path:** `POST /api/v1/handoff/generate`
* **Header:** `Authorization: Bearer <token>`
* **Status Code:** `200 OK`
* **Request Body:**
  ```json
  {
    "organization_id": "snapmeet",
    "repo_id": "snapmeet/billing-service",
    "outgoing_developer": "Rahul Sharma",
    "incoming_developer": "Aman Verma",
    "work_item": {
      "id": "wi_bill_204",
      "organization_id": "snapmeet",
      "external_id": "BILL-204",
      "source": "JIRA",
      "project_key": "BILL",
      "title": "Razorpay Invoicing & Webhook Retry Queue",
      "status": "DONE"
    },
    "pull_requests": [
      {
        "organization_id": "snapmeet",
        "repo_name": "snapmeet/billing-service",
        "pr_number": 88,
        "title": "Add retry queue for Razorpay webhooks",
        "state": "OPEN",
        "head_branch": "feat/BILL-204-razorpay-retry",
        "author_login": "rahul",
        "ci_status": "FAILED",
        "linked_issue_keys": ["BILL-204"]
      }
    ],
    "commits": [
      {
        "sha": "8f3a1bc49281a8b417c8d923fa1a80c98f121111",
        "message": "feat(billing): implement razorpay retry handler for BILL-204",
        "author_name": "Rahul Sharma",
        "author_email": "rahul@snapmeet.com",
        "files_changed": ["services/payment_retry.py"]
      }
    ]
  }
  ```
* **Response:** `HandoffPackage` with Executive Briefing, Action Checklist, dynamic inline citations (`[PR #88]`, `[Commit 8f3a1bc]`), and evaluated anomalies (e.g. `HW-03`).

---

## 5. Role-Scoped Grounded Chat Assistant (`/chat`)

* **Path:** `POST /api/v1/chat/query`
* **Header:** `Authorization: Bearer <token>`
* **Status Code:** `200 OK`
* **Request:**
  ```json
  {
    "organization_id": "snapmeet",
    "repo_id": "snapmeet/billing-service",
    "query": "What work is pending on BILL-204?",
    "context_keys": ["BILL-204", "PR #88"]
  }
  ```
* **Response:**
  ```json
  {
    "answer": "Synthesized context for repository `snapmeet/billing-service` in response to: 'What work is pending on BILL-204?'.",
    "citations": ["[Repo snapmeet/billing-service]", "[BILL-204]", "[PR #88]"],
    "repo_id": "snapmeet/billing-service",
    "access_granted": true
  }
  ```

---

## 6. Architecture Diagram & Text Spec Parsing (`/diagrams`)

* **Path:** `POST /api/v1/diagrams/parse`
* **Status Code:** `200 OK`
* **Request:**
  ```json
  {
    "filename": "payments_architecture.txt",
    "content": "Client -> API Gateway -> Billing Microservice -> PostgreSQL -> Redis Queue"
  }
  ```
* **Response:**
  ```json
  {
    "filename": "payments_architecture.txt",
    "component_count": 5,
    "components": [
      { "label": "Client", "confidence": 0.95 },
      { "label": "API Gateway", "confidence": 0.92 },
      { "label": "Billing Microservice", "confidence": 0.98 },
      { "label": "PostgreSQL", "confidence": 0.99 },
      { "label": "Redis Queue", "confidence": 0.95 }
    ]
  }
  ```

---

## 7. Historical Cold-Start Repository Sync (`/sync`)

* **Path:** `POST /api/v1/sync/historical`
* **Status Code:** `200 OK`
* **Request:**
  ```json
  {
    "organization_id": "snapmeet",
    "repo_path": ".",
    "max_commits": 50
  }
  ```
* **Response:**
  ```json
  {
    "organization_id": "snapmeet",
    "commits_indexed": 50,
    "status": "COMPLETED"
  }
  ```

---

## 8. Temporal Knowledge Graph & Decision Lineage (`/graph`)

* **Path:** `GET /api/v1/graph/lineage/{task_key}?organization_id={org_id}&repo_id={repo_id}`
* **Header:** `Authorization: Bearer <token>`
* **Status Code:** `200 OK`
* **Response:**
  ```json
  {
    "organization_id": "snapmeet",
    "task_key": "BILL-204",
    "decisions": [
      {
        "decision_id": "DEC-001",
        "title": "Adopt Redis SETNX for Webhook Idempotency",
        "rationale": "Prevents duplicate billing transactions during upstream network retries.",
        "status": "ACCEPTED",
        "supersedes": "In-Memory Deduplication Map"
      }
    ]
  }
  ```

---

## 9. Real-Time Alert Dispatcher (`/alerts`)

* **Path:** `POST /api/v1/alerts/dispatch`
* **Header:** `Authorization: Bearer <token>`
* **Status Code:** `200 OK`
* **Request:**
  ```json
  {
    "organization_id": "snapmeet",
    "task_key": "BILL-204",
    "repo_id": "snapmeet/billing-service",
    "anomaly": {
      "rule_id": "HW-03",
      "anomaly_type": "HW-03: Declared vs Observed State Mismatch",
      "triggered": true,
      "severity": "HIGH",
      "summary": "State Mismatch: Task declared DONE but PR #88 is incomplete/failing",
      "description": "Task BILL-204 marked DONE in Jira, but PR #88 has failing CI checks.",
      "affected_entities": ["PR #88 (CI Failed)"],
      "recommended_action": "Fix CI failures before closing ticket."
    }
  }
  ```
* **Response:** Returns formatted Slack Block Kit payload and `dispatched: true`.

---

## 10. Team Continuity, Organizations & Integrations (`/team`)

All endpoints in `/team` are backed by persistent PostgreSQL tables via Supabase client bindings with zero in-memory fallback stores.

### 10.1 Tenant Organizations Management
* **`POST /api/v1/team/organizations`** (`201 Created`): Creates a new organization in PostgreSQL `organizations` table (`id`, `name`, `domain`).
* **`GET /api/v1/team/organizations/{org_id}`** (`200 OK`): Fetches an organization record from PostgreSQL `organizations`.
* **`GET /api/v1/team/organizations`** (`200 OK`): Lists all tenant organizations.

### 10.2 Continuity Map & Single Point of Failure (SPOF)
* **Path:** `GET /api/v1/team/continuity-map?organization_id={org_id}`
* **Header:** `Authorization: Bearer <token>`
* **Status Code:** `200 OK`
* **Storage Backend:** PostgreSQL `user_repo_permissions` and `users` tables.
* **Response:**
  ```json
  {
    "organization_id": "snapmeet",
    "overall_continuity_score": 92.4,
    "service_risks": [
      {
        "repo_name": "snapmeet/billing-service",
        "primary_owner": "Rahul Sharma",
        "ownership_percentage": 0.85,
        "active_maintainers": 1,
        "risk_level": "CRITICAL",
        "remedy": "Immediate shadowing required: Rahul Sharma owns 85% of snapmeet/billing-service commits."
      }
    ]
  }
  ```

### 10.3 Active Anomaly Radar Feed
* **Path:** `GET /api/v1/team/anomalies-feed?organization_id={org_id}`
* **Header:** `Authorization: Bearer <token>`
* **Status Code:** `200 OK`
* **Storage Backend:** PostgreSQL `handoff_packages` table (`anomalies` JSONB column).

### 10.4 Handoff Transition History
* **Path:** `GET /api/v1/team/handoff-history?organization_id={org_id}`
* **Header:** `Authorization: Bearer <token>`
* **Status Code:** `200 OK`
* **Storage Backend:** PostgreSQL `handoff_packages` and `users` tables.

### 10.5 Tenant Integrations Management
* `GET /api/v1/team/{org_id}/integrations`: Returns real connected repositories from `user_repo_permissions`, Slack channels from `slack_channels`, and projects from `work_items`.
* `POST /api/v1/team/{org_id}/repos`: Registers new repository in `user_repo_permissions` table.
* `DELETE /api/v1/team/{org_id}/repos/{repo_id}`: Deletes repository permission from `user_repo_permissions`.
* `POST /api/v1/team/{org_id}/channels`: Adds Slack broadcast channel into PostgreSQL `slack_channels` table.
* `DELETE /api/v1/team/{org_id}/channels/{channel_id}`: Removes Slack channel from `slack_channels`.
* `POST /api/v1/team/{org_id}/projects`: Adds Jira/Linear project key into PostgreSQL `work_items` table.
* `DELETE /api/v1/team/{org_id}/projects/{project_id}`: Removes project record from `work_items`.

---

## 11. Role-Scoped Grounded AI Chat Assistant (`/chat`)

* **Path:** `POST /api/v1/chat/query`
* **Header:** `Authorization: Bearer <token>`
* **Status Code:** `200 OK` (or `403 Forbidden` if repository is unassigned / cross-tenant)
* **Security Gate:** Enforces Pre-Retrieval ACL (`PreRetrievalACL.guard_repo_access`) before context retrieval or prompt generation.
* **Request:**
  ```json
  {
    "organization_id": "snapmeet",
    "repo_id": "snapmeet/billing-service",
    "query": "What is the status of the razorpay retry implementation?",
    "context_keys": ["BILL-204", "PR #88"]
  }
  ```
* **Response:**
  ```json
  {
    "answer": "Repository snapmeet/billing-service [Repo snapmeet/billing-service] is tracking in-flight work item BILL-204...",
    "citations": [
      "[Repo snapmeet/billing-service]",
      "[BILL-204]",
      "[PR #88]"
    ],
    "repo_id": "snapmeet/billing-service",
    "access_granted": true,
    "provider": "gemini"
  }
  ```

# KAIRO: Slack Events API & Decision Extraction Pipeline

> **Domain:** Integrations & Connectors  
> **Document ID:** KAIRO-INT-SLACK  
> **Standard:** Real-Time Slack Events Ingress, Two-Stage Noise Filtering, Consensus Detection & 120-Day Backfill  
> **Status:** Production-Ready / Enforced in CI

---

## 1. Slack App Configuration & Scopes

1. **Slack App Creation:** Navigate to [api.slack.com/apps](https://api.slack.com/apps) $\rightarrow$ **Create New App** $\rightarrow$ **From scratch**.
2. **Bot Token Scopes (`OAuth & Permissions`):**
   * `channels:history` (read public channel messages)
   * `channels:read` (list public channels)
   * `groups:history` (read private channel discussions)
   * `users:read` (resolve author emails and canonical personas)
   * `reactions:read` (capture consensus votes like `:+1:`, `:white_check_mark:`, `:rocket:`)
   * `chat:write` (post handoff digests to leads)
3. **Event Subscriptions:**
   * **Request URL:** `https://<your-domain>/api/v1/webhooks/slack`
   * **Subscribe to Bot Events:**
     * `message.channels`
     * `message.groups`
     * `reaction_added`
4. **Environment Variables:**
   ```bash
   SLACK_SIGNING_SECRET="kairo_slack_signing_secret_production"
   SLACK_BOT_TOKEN="xoxb-your-slack-bot-token"
   MAX_DAILY_LLM_SPEND_USD=10.0
   SLACK_NOISE_MIN_WORDS=15
   DECISION_CONFIDENCE_THRESHOLD=0.70
   ENABLE_SLACK_INGESTION=true
   ENABLE_HISTORICAL_BACKFILL=true
   ```

---

## 2. Inbound Webhook Architecture & SLA

```mermaid
flowchart TD
    INGRESS["Inbound POST /api/v1/webhooks/slack"] --> CHALLENGE{"type == 'url_verification'?"}
    CHALLENGE -- Yes --> RESP_CHALLENGE["Return 200 OK with {'challenge': ...} (<10ms)"]
    
    CHALLENGE -- No --> SIG["Verify HMAC-SHA256 Signature\nCheck 5-Minute Replay Window"]
    SIG -- Invalid --> REJECT["HTTP 401 Unauthorized"]
    
    SIG -- Valid --> DEDUPE{"Event ID in Redis Cache?\n(X-Slack-Retry-Num)"}
    DEDUPE -- Duplicate --> DUP_ACK["Return 200 OK ('duplicate_ignored')"]
    
    DEDUPE -- New --> ENQUEUE["Offload to Celery:\nworkers.tasks.slack_task.process_slack_event"]
    ENQUEUE --> ACCEPT["Return 202 Accepted (<45ms SLA)"]
```

### Security & Ingress SLA
* **Sub-3-Second SLA:** Slack enforces a strict 3,000ms timeout before re-dispatching webhooks. The KAIRO endpoint executes signature verification and Redis deduplication, then returns `202 Accepted` in **< 45ms**, offloading all heavy compute to Celery workers.
* **Replay Protection:** Enforces `abs(time.time() - timestamp) <= 300` seconds. Any request older than 5 minutes is rejected with `HTTP 401 Unauthorized`.
* **Signature Verification:** Computes `v0=HMAC_SHA256(secret, "v0:" + timestamp + ":" + body)` and verifies using constant-time `hmac.compare_digest`.

---

## 3. Two-Stage Smart Noise-Filtering Layer

To prevent runaway LLM costs and avoid corrupting the Knowledge Graph with social banter, conversations pass through a hierarchical filter:

```mermaid
flowchart TD
    MSG["Slack Message Event"] --> THREAD_CHECK{"Is message part of a Thread?\n(thread_ts != None and != ts)"}
    
    THREAD_CHECK -- "NO (Standalone)" --> NOISE_FILTER["Standalone Heuristic Filter:\n1. Discard if bot_id present\n2. Discard if pure emoji/reaction\n3. Discard if stop phrase ('ok', 'done', 'lgtm')\n4. Discard if words < 15\n(Immunity granted if Jira Key or Tech Entity present)"]
    NOISE_FILTER -- Drop --> DISCARD_ORPHAN["Drop Message (Zero Compute Cost)"]
    NOISE_FILTER -- Pass --> INIT_THREAD["Initialize Thread State in slack_threads table"]
    
    THREAD_CHECK -- "YES (Thread Reply)" --> PRESERVE_REPLY["PRESERVE ALL REPLIES (Never Drop!)\n• 'Redis' = Candidate Proposal\n• 'LGTM' / +1 / 👍 = Consensus Approval Vote"]
    PRESERVE_REPLY --> APPEND_THREAD["Append to Thread State in PostgreSQL/Memory"]
    APPEND_THREAD --> DEBOUNCE["Debounce Task:\nevaluate_slack_thread (countdown=60s)"]
    
    DEBOUNCE --> WHOLE_GATE{"Whole-Thread Technical Gate:\n1. Total messages >= 2?\n2. Contains Jira Key OR Tech Entity?\n3. Contains Decision Verb OR Consensus Vote?"}
    WHOLE_GATE -- No --> DISCARD_THREAD["Mark Thread DISCARDED (Zero LLM Tokens)"]
    WHOLE_GATE -- Yes --> SPEND_GATE{"Daily Spend Cap Breached?\n(llm_usage_log < $10.00)"}
    SPEND_GATE -- Breached --> FALLBACK["Heuristic Grounded Extraction (Skip LLM)"]
    SPEND_GATE -- OK --> LLM_EXTRACT["Structured LLM Extraction Engine"]
```

### Why Thread Replies Are Never Dropped
In engineering communication, decisions often culminate in single-word technical proposals (e.g. *"Redis"*) followed by single-word affirmations (*"LGTM"*, *"+1"*, `:+1:`). Naive length or stop-phrase filters would discard these critical consensus points. In KAIRO:
* **Standalone filter applies ONLY to top-level messages.**
* **Thread replies are fully preserved** and formatted with consensus metadata for the extraction engine.

---

## 4. Structured LLM Decision Extraction & Confidence Gating

### Canonical Pydantic Schema (`packages.schemas.decision.ExtractedDecision`)
```python
class ExtractedDecision(BaseModel):
    title: str = Field(..., description="Short descriptive title of the technical decision")
    rationale: str = Field(..., description="Technical justification and trade-offs considered")
    jira_key: str | None = Field(None, description="Referenced Jira/Linear issue key, e.g. BILL-204")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    supersedes_decision_id: str | None = Field(None, description="Previous decision ID that this supersedes")
```

### Confidence Threshold Gatekeeper
* **Confidence $\ge 0.70$:** Committed directly into the Neo4j Knowledge Graph.
* **Confidence $< 0.70$:** Routed to PostgreSQL table `decision_review_queue` with status `PENDING_REVIEW` for lead engineer human approval.

---

## 5. Neo4j Graph Mutation & Provenance Lineage

Decisions are written using multi-tenant, idempotent Cypher queries:

```cypher
MATCH (t:Task {key: $jira_key, org_id: $org_id})
MERGE (d:Decision {id: $decision_id, org_id: $org_id})
ON CREATE SET d.title = $title,
              d.rationale = $rationale,
              d.source = 'SLACK_THREAD',
              d.confidence = $confidence,
              d.status = 'ACTIVE',
              d.timestamp = datetime()
ON MATCH SET d.title = $title,
             d.rationale = $rationale,
             d.confidence = $confidence
MERGE (t)<-[:JUSTIFIES]-(d)
WITH d
OPTIONAL MATCH (old:Decision {id: $supersedes_id, org_id: $org_id})
FOREACH (_ IN CASE WHEN old IS NOT NULL THEN [1] ELSE [] END |
    MERGE (d)-[:SUPERSEDES]->(old)
);
```

---

## 6. 120-Day Resumable Historical Cloud Backfill Engine

When an organization onboards or triggers historical synchronization via `POST /api/v1/sync/cloud`:

1. **GitHub Pull Requests:** Crawls closed/merged PRs, tracks `X-RateLimit-Remaining`, and links to `Task` nodes.
2. **Jira Backlog Issues:** Crawls issues updated in the last 120 days via JQL `updated >= -120d`.
3. **Slack Engineering Channels:** Crawls public `#eng-*` channels, evaluates threads through the whole-thread gate, and extracts decisions.
4. **Crash-Resilience:** Progress and cursor positions are stored in the PostgreSQL `backfill_jobs` table, enabling graceful pause and resume.
5. **Status Polling:** Frontend polls `GET /api/v1/sync/status/{job_id}` for real-time progress percentages and item counts.

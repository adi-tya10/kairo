# KAIRO: Slack Events API & Decision Extraction

> **Domain:** Integrations & Connectors  
> **Document ID:** KAIRO-INT-SLACK  
> **Target:** Slack Bolt & Events API for Technical Rationale Capture

---

## 1. Slack App Configuration

1. Navigate to [api.slack.com/apps](https://api.slack.com/apps) $\rightarrow$ **Create New App** $\rightarrow$ **From scratch**.
2. **Bot Token Scopes (`OAuth & Permissions`):**
   * `channels:history` (read public channel messages)
   * `channels:read` (list public channels)
   * `users:read` (resolve author emails)
   * `chat:write` (post handoff digests to leads)
3. **Event Subscriptions:**
   * Request URL: `https://<your-domain>/api/v1/webhooks/slack`
   * Subscribe to Bot Events: `message.channels`
4. Install to Workspace and set `SLACK_SIGNING_SECRET` and `SLACK_BOT_TOKEN` in `.env`.

---

## 2. Decision Extraction & NLP Pipeline

* **Timestamp Replay Check:** Verifies `abs(time.time() - timestamp) <= 300` seconds.
* **Signature Verification:** Computes HMAC-SHA256 signature using `SLACK_SIGNING_SECRET`.
* **Decision Extraction Engine:** Scans conversations for architectural decision keywords (*"decided to use"*, *"rejected alternative"*, *"outage caused by"*).
* **Graph Mutation:**
  ```cypher
  MATCH (t:Task {key: $jira_key})
  CREATE (d:Decision {
      id: $decision_id,
      title: $title,
      reason: $reason,
      rejected_alternatives: $rejected,
      status: 'ACTIVE',
      valid_from: $timestamp
  })
  MERGE (t)-[:CONSTRAINED_BY]->(d);
  ```

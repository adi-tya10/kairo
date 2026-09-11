# Changelog

All notable changes to the **KAIRO** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.3.0] - 2026-09-11

### Security & Access Control (P1 & P2 Remediations)
- **Zero Unauthenticated Tenant Endpoints:** Enforced strict `Depends(get_current_user)` authentication and `PreRetrievalACL.validate_tenant_access` tenant-scoping across `/api/v1/sync/historical`, `/api/v1/sync/cloud`, `/api/v1/sync/status/{job_id}`, and `/api/v1/diagrams/parse`.
- **Path Traversal Defenses:** Hardened historical sync directory path resolution against directory traversal (`..`) attempts, returning HTTP 400 Bad Request on path traversal probes.
- **RFC-Compliant Authentication Challenge:** Configured optional header parsing (`authorization: str | None = Header(None)`) in `get_current_user`, returning standard HTTP 401 Unauthorized for missing bearer tokens instead of FastAPI's default 422 Unprocessable Entity.
- **Cryptographic Token Hashing for Invitations:** Stored enterprise invitation tokens exclusively as cryptographic SHA-256 digests (`token_hash`) in PostgreSQL and memory stores; raw tokens are distributed only once at creation and never exposed in database columns or list APIs.
- **Eliminated Silent In-Memory Fallbacks:** Introduced typed `DatabaseWriteError` exceptions (`apps/api/app/core/errors.py`); in `APP_ENV=production`, database write failures immediately raise structured HTTP 500 errors and log structured JSON alerts instead of silently diverging into in-memory dictionaries.
- **Eradicated Bare Exception Handlers:** Replaced all repo-wide `except Exception: pass` anti-patterns with structured JSON logging and typed error escalation across identity, handoff, context, and webhook ingress controllers.

### Architecture & Database (P1 & P3 Remediations)
- **PostgreSQL Migrations 004 & 005 Applied:** Applied user password hashing (`004_user_passwords_and_seed.sql`) and cloud backfill/Slack decisions (`005_backfill_and_slack_decisions.sql`) to active Supabase PostgreSQL cluster.
- **Vector Similarity Search RPC (Migration 006):** Implemented and applied `006_vector_similarity_search.sql` adding the `match_embeddings` stored procedure utilizing `pgvector` cosine similarity (`1 - (embeddings.embedding <=> query_embedding)`) and IVFFlat index traversal for high-performance multi-tenant semantic retrieval.
- **Desktop HUD Environment Decoupling:** Replaced hardcoded `localhost:8000` API endpoints in `apps/desktop/src/App.tsx` and `ChatAssistant.tsx` with dynamic `import.meta.env.VITE_KAIRO_API_URL`, providing production default fallback and dedicated `.env.production` and `.env.development` configurations.
- **Production Guardrails on Embeddings Pipeline:** Workers require valid LLM API credentials when operating in `APP_ENV=production`, preventing silent heuristic fallbacks in production pipelines.
- **Documentation Alignment:** Updated `README.md` and engine docstrings to accurately document CV layout parser heuristics and the 2-tier deterministic Git work resolution model.
- **Mandatory Remote GitHub Synchronization:** Updated `AGENTS.md` (§4.1, §11.1, §13, §17) to mandate that after every finalized decision, bug fix, or milestone, verified code must be committed and pushed immediately to GitHub (`git push origin <branch>`).

### Testing & Verification
- **Full Test Suite Passing:** Verified all unit, integration, and contract tests passing across auth, sync, diagrams, security error handlers, enterprise identity, Slack webhooks, and pgvector chat retrieval. Zero regressions.
- **CI Pipeline Hardening:** Resolved Ruff linting formatting, fixed Mypy typing across 92 source files, synchronized Redis and memory deduplication caches, and validated offline test fixture execution for embedding tasks.

---

## [1.2.0] - 2026-09-10

### Added
- **Production-Grade Slack Inbound Webhook Ingestion:** Mounted `POST /api/v1/webhooks/slack` with sub-45ms `202 Accepted` response SLA, URL challenge handling, cryptographic HMAC-SHA256 signature verification (`verify_slack_signature` with 5-minute replay prevention), and Redis-backed event ID deduplication (`event_id`).
- **Smart 3-Layer Pre-LLM Noise Filtering:** Implemented a differentiated noise filtering engine (`workers/tasks/slack_task.py`) that filters top-level chatter while strictly preserving thread replies—safeguarding short architectural proposals (e.g. "Redis", "Kafka") and affirmative consensus votes ("LGTM", "+1", emoji reactions).
- **Whole-Thread Decision Gate & Spend Cap Protection:** Integrated a whole-thread keyword filter (requires $\ge 2$ replies, $\ge 15$ words, technical signal matching) avoiding zero-value LLM costs, combined with a hard per-tenant daily spend ceiling (`$10.00`) queried against `llm_usage_log`.
- **Confidence-Gated Graph Lineage Mutations:** Structured LLM decision extraction (`LLMService.extract_decision_from_thread`) strictly validated against `ExtractedDecision` schema; decisions $\ge 0.70$ mutate Neo4j AuraDB with `[:JUSTIFIES]` and `[:SUPERSEDES]` edges, while decisions $< 0.70$ are quarantined to PostgreSQL `decision_review_queue` for human sign-off.
- **Resumable 120-Day Cloud Historical Backfill Engine:** Implemented `POST /api/v1/sync/cloud` and `GET /api/v1/sync/status/{job_id}` orchestrating GitHub, Jira, and Slack historical backfills backed by Celery (`sync_historical_cloud_data`) with cursor-based checkpointing in `backfill_jobs`.
- **Relational & Graph Schema Migrations:** Added PostgreSQL migration `005_backfill_and_slack_decisions.sql` (`slack_threads`, `decision_review_queue`, `llm_usage_log`, `backfill_jobs`) and Neo4j Cypher migration `002_decision_lineage.cypher` (multi-tenant composite indexes on source, confidence, timestamp).

### Testing & Verification
- **100% Passing Webhook & Engine Suite:** Added 15 comprehensive unit and contract tests in `apps/api/tests/test_slack_webhook.py` covering URL verification, valid/invalid HMAC signatures, replay attack rejection, event deduplication, thread filtering, consensus vote detection, confidence gating, spend cap halts, and backfill status polling. All 38 existing tests pass with zero regressions.

---

## [1.1.1] - 2026-09-09

### Security & Identity
- **Invitation Token Replay Prevention:** Synchronized database and in-memory invitation status upon acceptance in `IdentityService` to prevent token reuse, replay attacks, and state divergence.
- **CORS Configuration & Render Domain Regex:** Updated `CORS_ORIGINS` parsing to flexibly handle both comma-separated and JSON string formats in `pydantic-settings`, and introduced `allow_origin_regex` to support dynamic OnRender preview and staging subdomains.

### Added & Improvements
- **Transactional Brevo Email Service & Boarding Pass Templates:** Implemented transactional invitation emails via Brevo SMTP featuring styled boarding pass HTML layouts, production fallback URL resolution, and hardened SMTP transport error recovery.
- **Dynamic Desktop HUD Onboarding & Download Flow:** Added dedicated automated installer scripts (`public/install.ps1` for Windows, `public/install.sh` for Unix/macOS) and wired live download onboarding flow in `apps/web`.
- **Uptime Monitoring & Health Checks:** Added `HEAD` method support on `/` and `/health` to allow zero-payload heartbeat probes from external uptime monitoring bots.

### Infrastructure & Cloud Deployment
- **Render Cloud Blueprint (`render.yaml`):** Created full infrastructure blueprint with dynamic port binding and embedded Celery start script for unified deployment.
- **Cloud Redis & Worker Resilience:** Added `rediss://` SSL support for Celery with Upstash Redis, connection pool socket timeouts, client reset on reconnect, explicit task result TTLs, and graceful startup retries during transient database outages.
- **Container Packaging:** Added `cv_pipeline` module to the Docker container context to resolve image build and import dependencies.

---

## [1.1.0] - 2026-09-08

### Added
- **Production-Grade Data Persistence:** Webhook ingestion (`workers/tasks/ingest.py`) idempotently writes incoming GitHub, Jira, Linear, and GitLab payloads to PostgreSQL `events_raw`, upserts to `work_items`, and dynamically synchronizes nodes (`:Task`, `:PullRequest`, `:Developer`, `:Commit`) and relationships in Neo4j AuraDB.
- **Relational Identity Persistence:** Replaced flat file stores (`enterprise_identity_store.json`, `users_store.json`) with PostgreSQL-backed `IdentityService` maintaining transactional state for teams, memberships, invitations, devices, external identities, and PBKDF2/Argon2-hashed passwords.
- **Dynamic Semantic Embeddings Pipeline:** Implemented `workers/tasks/embeddings.py` generating deterministic 768-dimensional L2-normalized vector embeddings persisted into PostgreSQL `embeddings` table with pgvector cosine distance indexing.
- **Real RAG Chat Context Retrieval:** Overhauled `/api/v1/chat/query` to dynamically fetch relevant context from pgvector cosine similarity search, active work items, and Neo4j architectural decision subgraphs.
- **Dynamic Anomaly Handoffs:** `/api/v1/handoff/generate` evaluates active hidden-work anomalies (`HW-01` to `HW-05`) directly against live PostgreSQL `work_items` and commits, persisting generated handoff packages to `handoff_packages`.
- **Async External Dispatch:** `/api/v1/alerts/slack` dispatches to webhook endpoints via async `httpx.AsyncClient` with bounded timeouts and structured responses.
- **Real CV Pipeline:** Replaced mock box generator in `cv_pipeline/diagram_parser.py` with PIL image contour analysis, bounding box extraction, and color classification.

### Security
- **Strict Webhook HMAC Verification:** Enforced SHA-256 HMAC signature verification on GitHub (`X-Hub-Signature-256`), Jira, Linear, and GitLab webhook controllers with secure fail-closed semantics.
- **Token Hardening & Unified Auth:** Eradicated demo token bypass strings across API and Desktop HUD (`apps/desktop/src/App.tsx`). Standardized all protected routes on `Depends(get_current_user)`.
- **Brute-Force Protection:** Added sliding-window rate limiting on `/api/v1/auth/login`.

### Testing & Verification
- **High Test Coverage:** Raised test coverage to 85.06% across 132 passing unit, integration, and security tests. All TypeScript suites in `apps/web` and `apps/desktop` compile with zero errors.


---

## [1.0.0] - 2026-08-26

### Added
- **Core Temporal Knowledge Graph:** Integrated Supabase PostgreSQL 16 (`pgvector`) and Neo4j AuraDB 5+ with Cypher uniqueness constraints and temporal validity indexing.
- **Multimodal Diagram Ingestion Pipeline:** Computer vision parser leveraging OpenCV, PaddleOCR, and Docling for extracting service dependencies and data flow arrows from PNG/JPEG architecture diagrams.
- **Hidden-Work & Anomaly Detection Engine:** Automated heuristic rule engine evaluating rules `HW-01` through `HW-05` (Jira vs. GitHub discrepancy, shadow commitments, historical incident regressions, architecture drift, orphaned dependencies).
- **Cryptographic Evidence Manifest:** Citation verification engine mapping synthesized claims directly to Git commit SHAs, webhook delivery GUIDs, and visual bounding boxes.
- **Webhook Ingress Layer:** Sub-20ms ingestion gateway with HMAC-SHA256 signature verification for Jira Cloud, GitHub App (`pull_request`, `push`, `check_run`), and Slack Events API.
- **Interactive Handoff Dashboard:** Next.js 14 App Router web application featuring Shadcn/UI components, interactive drill-down citations, and a context Q&A panel.
- **Universal AI Contributor Guide:** Comprehensive, tool-agnostic `AGENTS.md` specifying architecture boundaries, security rules, and coding standards.

### Security
- Implemented PostgreSQL Row-Level Security (RLS) and Cypher tenant isolation.
- Pre-prompt source ACL pruning to prevent privilege escalation during LLM context synthesis.
- AES-256-GCM encryption at rest for third-party OAuth tokens and secrets.
- Enforced strict Anti-Surveillance Guardrails (elimination of developer velocity/productivity tracking).

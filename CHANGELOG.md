# Changelog

All notable changes to the **KAIRO** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

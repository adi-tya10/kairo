# Changelog

All notable changes to the **KAIRO** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Planned
- Enterprise SAML 2.0 / Okta SSO integration.
- Bidirectional Notion sync worker with real-time block-level change streams.
- Automated Slack Bot interactive DM handoff approvals.

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

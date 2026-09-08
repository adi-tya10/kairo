# KAIRO: Domain-Wise Technical Documentation Portal

> **Standard:** Enterprise Architecture & Technical Documentation Index  
> **Master Revision:** 2026.1  
> **Root Hub:** [README.md](file:///c:/Users/adity/OneDrive/Personal%20Vault/Desktop/Kairo/README.md) | [ARCHITECTURE.md](file:///c:/Users/adity/OneDrive/Personal%20Vault/Desktop/Kairo/ARCHITECTURE.md) | [SECURITY.md](file:///c:/Users/adity/OneDrive/Personal%20Vault/Desktop/Kairo/SECURITY.md) | [AGENTS.md](file:///c:/Users/adity/OneDrive/Personal%20Vault/Desktop/Kairo/AGENTS.md)

---

## 🏛️ Domain Architecture & Documentation Structure

```
docs/
├── 📁 01-architecture-and-system/     # Core Architecture, Data Models, Engines & ADRs
│   ├── 📄 overview.md                 # High-Level Architecture, Implementation Matrix & Commands
│   ├── 📄 data-models.md              # Pydantic v2 Models, PostgreSQL 16 (pgvector) & Neo4j Cypher
│   ├── 📄 engines-and-algorithms.md   # State Machine, Deterministic HW-01..05 Rules & SPOF Engine
│   ├── 📄 evidence-resolution-and-verification.md # 4-Tier Hybrid Matching & Grounding
│   ├── 📄 desktop-overlay-and-access-control.md   # Tauri HUD, Git Watcher & Pre-Retrieval ACLs
│   └── 📁 adrs/                       # Formal Architectural Decision Records
│       ├── 📄 ADR-001-modular-monolith.md
│       ├── 📄 ADR-002-dual-store-postgres-neo4j.md
│       └── 📄 ADR-003-deterministic-rules-grounded-synthesis.md
├── 📁 02-integrations-and-connectors/ # Third-Party Integration Guides & Webhooks
│   ├── 📄 jira-cloud.md               # Jira Cloud OAuth, Webhook Setup & Event Schemas
│   ├── 📄 github-app.md               # GitHub App Permissions & HMAC-SHA256 Ingress
│   ├── 📄 linear-app.md               # Linear App Webhooks & Work Item Normalization
│   ├── 📄 gitlab.md                   # GitLab Merge Request & Pipeline Webhooks
│   ├── 📄 slack-events.md             # Slack Bolt App, Events API & Decision Capture
│   └── 📄 notion-and-documents.md     # Notion Sync & Multimodal Diagram CV Pipeline
├── 📁 03-api-and-contracts/           # REST Endpoints & Error Protocols
│   ├── 📄 rest-endpoints.md           # OpenAPI 3.1 REST API Reference & Schemas (10 Modules)
│   ├── 📄 webhooks.md                 # Ingress Contracts & Idempotency Guarantees
│   └── 📄 error-handling.md           # RFC 7807 Problem Details & Typed KairoError Classes
├── 📁 04-security-and-compliance/     # Threat Models, IAM & Compliance
│   ├── 📄 threat-model.md             # STRIDE Threat Analysis & OWASP Mitigations
│   ├── 📄 identity-and-access.md      # Multi-Tenant RLS & Pre-Prompt ACL Pruning
│   ├── 📄 cryptography-and-secrets.md # AES-256-GCM Storage & Secret Hygiene
│   └── 📄 ethical-ai-guardrails.md    # Anti-Surveillance Policy & Citation Integrity
├── 📁 05-devops-and-operations/       # Deployment, Observability & Runbooks
│   ├── 📄 local-development.md        # Local Dev Runbook, uv, pnpm & Tunneling
│   ├── 📄 deployment-guide.md         # $0 Free-Tier vs. Kubernetes EKS/GKE Helm
│   └── 📄 observability.md            # OpenTelemetry, Prometheus & Alerting Rules
├── 📁 06-quality-and-testing/         # Testing Strategies & CI Gates
│   ├── 📄 test-pyramid.md             # Test Pyramid, Testcontainers & Mocking
│   └── 📄 coverage-and-ci-gates.md    # Coverage Enforcement & CI Merge Gates
└── 📁 07-research-and-benchmarks/     # Empirical Research & Evaluation
    ├── 📄 research-questions.md       # Core Research Questions (RQ1 to RQ5)
    └── 📄 baseline-benchmarks.md      # Baselines B1 to B5 & Quantitative Metrics
```

---

## 🔗 Quick Links by Engineering Role

* **Backend Engineers:** [01-architecture-and-system/data-models.md](file:///c:/Users/adity/OneDrive/Personal%20Vault/Desktop/Kairo/docs/01-architecture-and-system/data-models.md) | [03-api-and-contracts/rest-endpoints.md](file:///c:/Users/adity/OneDrive/Personal%20Vault/Desktop/Kairo/docs/03-api-and-contracts/rest-endpoints.md)
* **AI / ML Engineers:** [01-architecture-and-system/engines-and-algorithms.md](file:///c:/Users/adity/OneDrive/Personal%20Vault/Desktop/Kairo/docs/01-architecture-and-system/engines-and-algorithms.md) | [07-research-and-benchmarks/research-questions.md](file:///c:/Users/adity/OneDrive/Personal%20Vault/Desktop/Kairo/docs/07-research-and-benchmarks/research-questions.md)
* **DevOps / SRE:** [05-devops-and-operations/deployment-guide.md](file:///c:/Users/adity/OneDrive/Personal%20Vault/Desktop/Kairo/docs/05-devops-and-operations/deployment-guide.md) | [05-devops-and-operations/observability.md](file:///c:/Users/adity/OneDrive/Personal%20Vault/Desktop/Kairo/docs/05-devops-and-operations/observability.md)
* **Security & Auditors:** [04-security-and-compliance/threat-model.md](file:///c:/Users/adity/OneDrive/Personal%20Vault/Desktop/Kairo/docs/04-security-and-compliance/threat-model.md) | [04-security-and-compliance/identity-and-access.md](file:///c:/Users/adity/OneDrive/Personal%20Vault/Desktop/Kairo/docs/04-security-and-compliance/identity-and-access.md)
* **AI Coding Assistants:** [AGENTS.md](file:///c:/Users/adity/OneDrive/Personal%20Vault/Desktop/Kairo/AGENTS.md)

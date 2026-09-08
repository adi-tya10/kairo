# KAIRO: STRIDE Threat Model & Security Mitigations

> **Domain:** Security, Privacy & Compliance  
> **Document ID:** KAIRO-SEC-THREAT  
> **Framework:** STRIDE + OWASP Top 10 API Security

---

## 1. System Threat Matrix

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               STRIDE THREAT MITIGATION MATRIX                          │
│                                                                                        │
│   [S] Spoofing     ──► HMAC-SHA256 Signatures (X-Hub-Signature-256 / Jira Tokens)      │
│   [T] Tampering    ──► Cryptographic Provenance (Git Commit SHAs / Event IDs)          │
│   [R] Repudiation  ──► Immutable Audit Trails in PostgreSQL audit_logs                 │
│   [I] Disclosure   ──► Pre-Prompt ACL Subgraph Pruning & Tenant RLS                    │
│   [D] Denial (DoS) ──► Redis Sliding-Window Rate Limiting & Webhook Idempotency        │
│   [E] Elevation    ──► Supabase PostgreSQL RLS + Neo4j Tenant Graph Isolation          │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. OWASP API Top 10 Mitigations

* **API1: Broken Object Level Authorization (BOLA):** Strict RLS enforcing `WHERE organization_id = :org_id` on every query.
* **API2: Broken Authentication:** Short-lived Supabase JWTs with rotating HMAC keys and PKCE auth flows.
* **API3: Broken Object Property Level Authorization:** Pydantic v2 schemas reject unexpected request payload fields.
* **API4: Unrestricted Resource Consumption:** Ingress rate limiting (100 req/min for webhooks, 20 req/min for Q&A).
* **API8: Security Misconfiguration:** Strict CORS whitelist and security headers (CSP, HSTS, X-Content-Type-Options).

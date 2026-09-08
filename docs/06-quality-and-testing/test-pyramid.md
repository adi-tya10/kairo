# KAIRO: Test Pyramid, Toolchains & Mocking Strategy

> **Domain:** Quality Assurance & Testing  
> **Document ID:** KAIRO-QA-PYRAMID  
> **Tools:** pytest, testcontainers, Vitest, Playwright

---

## 1. Testing Pyramid Distribution

* **Unit Tests (70%):** State machine, anomaly rules (`HW-01`..`HW-05`), evidence ranker, diagram spatial math, semantic vector similarity preservation.
* **Integration & Security Tests (20%):** Multi-tenant isolation verification across Chat RAG and Context Work-Items, distributed Redis-backed rate limiting across multi-replica instances, Celery webhook pipelines, and PostgreSQL + Neo4j transactional sync.
* **End-to-End Tests (10%):** Playwright automated browser flows covering the handoff briefing dashboard and interactive Q&A.

---

## 2. Test Execution Commands

```bash
# Backend unit & integration tests with coverage
cd apps/api
pytest --cov=app --cov-fail-under=85

# Frontend unit & component tests
cd apps/web
pnpm test

# Browser E2E suite
pnpm test:e2e
```

# ADR-001: Event-Driven Modular Monolith Architecture

> **Status:** Accepted  
> **Date:** 2026-08-26  
> **Deciders:** Principal Software Architect, Tech Leads  

---

## Context
Kairo requires real-time webhook ingestion (< 20ms response), continuous anomaly detection across heterogeneous data streams, and multimodal computer vision extraction. Fully distributed microservices introduce heavy operational overhead (service meshes, distributed transactions/Saga, cross-network serialization, high hosting cost). A naive monolith risks blocking the HTTP ingress thread pool during heavy OCR and LLM inference jobs.

## Decision
Adopt an **Event-Driven Modular Monolith** in Python (FastAPI) paired with an asynchronous Celery worker pipeline backed by Upstash Redis:
* Synchronous API ingress layer handles signature verification, rate-limiting, and immediately queues jobs.
* Decoupled asynchronous Celery workers execute OCR, vector embedding generation, Cypher graph transactions, and LLM synthesis.
* Internal package boundaries (`apps/api/app/engines/`, `apps/api/app/services/`) strictly enforce dependency isolation.

## Consequences
* **Positive:** Sub-50ms API responsiveness, simplified deployment, local transactional integrity, and $0 free-tier hosting capability.
* **Trade-off:** Requires disciplined modular boundaries to prevent spaghetti coupling across Python packages.

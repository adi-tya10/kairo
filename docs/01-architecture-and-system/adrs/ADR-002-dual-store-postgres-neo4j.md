# ADR-002: Dual-Store Strategy (PostgreSQL + Neo4j AuraDB)

> **Status:** Accepted  
> **Date:** 2026-08-26  
> **Deciders:** Principal Software Architect, Database Architect  

---

## Context
Kairo manages two fundamentally different data workloads:
1. **Relational & Vector Workloads:** Multi-tenant accounts, user credentials, normalized work item tables, audit logs, and dense 768-dim semantic chunk embeddings.
2. **Temporal Graph Workloads:** Multidirectional dependencies (`Task` $\rightarrow$ `PR` $\rightarrow$ `Service` $\rightarrow$ `Incident`), dynamic ownership shifts (`WORKED_ON`), and decision superseding lineages (`valid_from`, `valid_to`).

Relational DBs struggle with recursive multi-hop graph traversals; pure graph DBs lack native dense vector indexes combined with robust relational ACID controls.

## Decision
Implement a **Specialized Dual-Store Storage Backbone**:
* **Supabase PostgreSQL 16+:** Authoritative relational source of truth, user sessions, Row-Level Security (RLS) policies, and dense vector index (`pgvector` with IVFFlat cosine search).
* **Neo4j AuraDB 5+:** Labeled property knowledge graph maintaining entity topology, time-sliced validity edges, and 2-hop handoff traversal queries.

## Consequences
* **Positive:** Sub-millisecond graph traversals combined with enterprise ACID relational integrity and native vector search.
* **Trade-off:** Ingestion workers must execute dual-write operations across PostgreSQL and Neo4j within idempotent Celery tasks.

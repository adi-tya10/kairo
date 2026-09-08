# KAIRO: Cloud & Kubernetes Production Deployment Guide

> **Domain:** DevOps & Infrastructure  
> **Document ID:** KAIRO-OPS-DEPLOY  
> **Target:** Serverless Free-Tier & Enterprise Kubernetes (EKS/GKE)

---

## 1. Dual-Tier Deployment Architectures

```mermaid
flowchart LR
    subgraph VERCEL ["Vercel (Hobby Tier - $0)"]
        FE["Next.js 14 Dashboard"]
    end

    subgraph CLOUD_COMPUTE ["Render / Railway / Kubernetes"]
        API["FastAPI Ingress Layer"]
        WORKER["Celery Task Workers"]
    end

    subgraph DATABASES ["Managed Cloud Stores"]
        SUPA["Supabase Postgres (pgvector)"]
        NEO["Neo4j AuraDB Free"]
        UPSTASH["Upstash Serverless Redis"]
    end

    FE --> API
    API --> UPSTASH --> WORKER
    API & WORKER --> SUPA & NEO
```

---

## 2. Zero-Downtime Schema Migrations

```bash
# Relational Migrations (PostgreSQL)
supabase db push --include-all

# Graph Migrations (Neo4j AuraDB)
python -m graph.apply_migrations
```

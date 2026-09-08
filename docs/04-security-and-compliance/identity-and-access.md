# KAIRO: Identity, Access Management & Pre-Prompt ACL Filtering

> **Domain:** Security, Privacy & Compliance  
> **Document ID:** KAIRO-SEC-IAM  
> **Standard:** Zero-Trust Access Control & Tenant Partitioning

---

## 1. Multi-Tenant Authorization Layers

### PostgreSQL Row-Level Security (RLS)
```sql
ALTER TABLE work_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY work_items_tenant_isolation ON work_items
    FOR ALL
    USING (organization_id = (auth.jwt() ->> 'organization_id')::uuid);
```

### Neo4j Cypher Tenant Scoping
```cypher
MATCH (t:Task {organization_id: $org_id})
MATCH (u:User {organization_id: $org_id, id: $user_id})
```

---

## 2. Pre-Prompt ACL Filtering (Zero Privilege Escalation)

Before generating an LLM handoff briefing for user $U_{to}$:
1. The engine queries source ACLs for user $U_{to}$ across private GitHub repositories, Jira projects, and Slack channels.
2. Any entity or document chunk that $U_{to}$ lacks explicit permission to access is **pruned from the retrieval subgraph** before prompt generation.
3. The LLM cannot summarize or leak information it never receives.

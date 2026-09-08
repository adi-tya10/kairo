# KAIRO: Data Models & Knowledge Graph Ontology

> **Domain:** Architecture & System Design  
> **Document ID:** KAIRO-ARCH-DATA  
> **Databases:** Supabase PostgreSQL 16+ (Relational + Vector) & Neo4j AuraDB 5+ (Graph)

---

## 1. Dual-Store Storage Strategy

* **PostgreSQL (Supabase):** Manages relational metadata, multi-tenant isolation, user sessions, raw audit logs, and dense vector embeddings (`pgvector`) for semantic chunk search.
* **Neo4j AuraDB:** Stores entity topology, multidirectional dependencies, ownership changes, temporal validity windows, and decision lineage `(Decision)-[:SUPERSEDES]->(OldChoice)`.
* **JSON File Store & Dynamic Tenant Registry:** Provides local stateful tenant credentials and organization service registries (`apps/db/users_store.json`) for seamless zero-cloud local testing and standalone runtime.

---

## 2. Pydantic v2 Core Domain Models (`packages/schemas/`)

KAIRO enforces strict Pydantic v2 schema validation across all API routes, Celery worker payloads, and synthesis engines:

### 2.1. Work Item (`packages/schemas/work_item.py`)
```python
class WorkItemStatus(str, Enum):
    BACKLOG = "BACKLOG"
    TO_DO = "TO_DO"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"
    CLOSED = "CLOSED"

class WorkItemSource(str, Enum):
    JIRA = "JIRA"
    TAIGA = "TAIGA"
    GITHUB_ISSUE = "GITHUB_ISSUE"
    LINEAR = "LINEAR"
    GITLAB = "GITLAB"

class WorkItem(BaseModel):
    id: str
    organization_id: str
    external_id: str  # e.g. "BILL-204" or "ENG-104"
    source: WorkItemSource
    project_key: str
    title: str
    description: str | None = None
    status: WorkItemStatus
    assignee_id: str | None = None
    assignee_email: str | None = None
    assignee_name: str | None = None
    creator_id: str | None = None
    created_at: datetime
    updated_at: datetime
```

### 2.2. Anomaly Rule Result (`packages/schemas/anomaly.py`)
```python
class AnomalyType(str, Enum):
    HW_01 = "HW-01: Shadow Work / Unlinked Activity"
    HW_02 = "HW-02: Stalled In-Flight Work"
    HW_03 = "HW-03: Declared vs Observed State Mismatch"
    HW_04 = "HW-04: Architecture Documentation Drift"
    HW_05 = "HW-05: Orphaned Critical Dependency"

class AnomalySeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AnomalyRuleResult(BaseModel):
    rule_id: str  # "HW-01", "HW-02", etc.
    anomaly_type: AnomalyType
    triggered: bool
    severity: AnomalySeverity
    summary: str
    description: str
    affected_entities: list[str]
    recommended_action: str
    evidence_manifest: list[dict[str, Any]] = []
    detected_at: datetime
```

### 2.3. Handoff Package & Citations (`packages/schemas/handoff.py`)
```python
class EvidenceType(str, Enum):
    PULL_REQUEST = "PULL_REQUEST"
    COMMIT = "COMMIT"
    JIRA_ISSUE = "JIRA_ISSUE"
    SLACK_THREAD = "SLACK_THREAD"
    FILE_DIFF = "FILE_DIFF"
    DECISION_RECORD = "DECISION_RECORD"

class EvidenceCitation(BaseModel):
    citation_key: str  # e.g. "[PR #88]", "[Commit 8f3a1bc]"
    evidence_type: EvidenceType
    identifier: str
    title: str
    url: str | None = None
    snippet: str | None = None
    confidence: float  # 0.0 to 1.0

class HandoffPackage(BaseModel):
    handoff_id: str
    organization_id: str
    task_key: str
    from_user_id: str
    to_user_id: str
    briefing: ExecutiveBriefing
    anomalies: list[AnomalyRuleResult] = []
    evidence_manifest: list[EvidenceCitation] = []
    status: str = "ACTIVE"
    created_at: datetime
    acknowledged_at: datetime | None = None
```

### 2.4. Permissions & ACL (`packages/schemas/permissions.py`)
```python
class UserPermissionProfile(BaseModel):
    organization_id: str
    user_id: str
    email: str
    github_username: str | None = None
    jira_account_id: str | None = None
    allowed_repo_ids: list[str] = []
    allowed_project_keys: list[str] = []
    is_org_admin: bool = False
    synced_at: datetime
```

---

## 3. PostgreSQL Relational Schema (DDL)

```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. TENANCY & AUTHENTICATION
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email TEXT NOT NULL,
    display_name TEXT NOT NULL,
    avatar_url TEXT,
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('admin', 'lead', 'member')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (organization_id, email)
);
CREATE INDEX idx_users_org ON users(organization_id);

-- 2. THIRD-PARTY INTEGRATIONS & SECRETS
CREATE TABLE integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    provider TEXT NOT NULL CHECK (provider IN ('jira', 'github', 'linear', 'gitlab', 'slack', 'notion', 'gdrive')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revoked', 'error')),
    encrypted_credentials TEXT NOT NULL, -- AES-256-GCM encrypted tokens
    webhook_secret TEXT,
    config JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (organization_id, provider)
);

-- 3. PROJECTS & NORMALIZED WORK ITEMS
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_projects_org ON projects(organization_id);

CREATE TABLE work_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source TEXT NOT NULL CHECK (source IN ('jira', 'github', 'linear', 'gitlab', 'slack', 'notion')),
    external_id TEXT NOT NULL,
    item_type TEXT NOT NULL CHECK (item_type IN ('issue', 'pr', 'commit', 'thread', 'spec')),
    title TEXT NOT NULL,
    declared_status TEXT,
    reconstructed_status TEXT,
    assignee_id UUID REFERENCES users(id) ON DELETE SET NULL,
    raw_payload JSONB NOT NULL,
    source_created_at TIMESTAMPTZ,
    source_updated_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (project_id, source, external_id)
);
CREATE INDEX idx_work_items_project ON work_items(project_id);
CREATE INDEX idx_work_items_external ON work_items(source, external_id);

-- 4. DOCUMENTS, DIAGRAMS & VECTOR EMBEDDINGS
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    source TEXT NOT NULL CHECK (source IN ('upload', 'notion', 'gdrive')),
    filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    doc_type TEXT NOT NULL CHECK (doc_type IN ('spec', 'architecture_diagram', 'sop', 'postmortem')),
    processing_status TEXT NOT NULL DEFAULT 'pending' CHECK (processing_status IN ('pending', 'processing', 'completed', 'failed')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    page_number INT,
    bounding_box JSONB, -- {x, y, w, h}
    embedding VECTOR(768),
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_document_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 5. HANDOFF EVENTS & GENERATED PACKAGES
CREATE TABLE handoff_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    from_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    to_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    trigger_type TEXT NOT NULL CHECK (trigger_type IN ('reassignment', 'offboarding', 'leave', 'emergency')),
    status TEXT NOT NULL DEFAULT 'processing' CHECK (status IN ('processing', 'ready', 'failed')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE handoff_packages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    handoff_event_id UUID NOT NULL REFERENCES handoff_events(id) ON DELETE CASCADE,
    reconstructed_state TEXT NOT NULL,
    summary_markdown TEXT NOT NULL,
    completed_items JSONB NOT NULL DEFAULT '[]'::JSONB,
    remaining_items JSONB NOT NULL DEFAULT '[]'::JSONB,
    decisions JSONB NOT NULL DEFAULT '[]'::JSONB,
    risks_detected JSONB NOT NULL DEFAULT '[]'::JSONB,
    recommended_first_actions JSONB NOT NULL DEFAULT '[]'::JSONB,
    evidence_manifest JSONB NOT NULL DEFAULT '[]'::JSONB,
    generated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 6. AUDIT LOGGING & COMPLIANCE
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    actor_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    target_resource TEXT NOT NULL,
    ip_address TEXT,
    metadata JSONB DEFAULT '{}'::JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_audit_org ON audit_logs(organization_id, created_at);
```

---

## 4. Neo4j Knowledge Graph Ontology & Cypher Slicing

```cypher
// 1. Uniqueness Constraints
CREATE CONSTRAINT user_id_unique IF NOT EXISTS FOR (u:User) REQUIRE u.id IS UNIQUE;
CREATE CONSTRAINT project_id_unique IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE;
CREATE CONSTRAINT task_id_unique IF NOT EXISTS FOR (t:Task) REQUIRE t.id IS UNIQUE;
CREATE CONSTRAINT pr_id_unique IF NOT EXISTS FOR (pr:PullRequest) REQUIRE pr.id IS UNIQUE;
CREATE CONSTRAINT service_id_unique IF NOT EXISTS FOR (s:Service) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT decision_id_unique IF NOT EXISTS FOR (d:Decision) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT incident_id_unique IF NOT EXISTS FOR (i:Incident) REQUIRE i.id IS UNIQUE;

// 2. Query Decision Lineage & Supersedes Traversal
MATCH (t:Task {key: $task_key, organization_id: $org_id})<-[:JUSTIFIES]-(d:Decision)
OPTIONAL MATCH (d)-[:SUPERSEDES]->(old:Decision)
RETURN d.id AS decision_id, d.title AS title, d.rationale AS rationale, d.status AS status, old.title AS supersedes;
```

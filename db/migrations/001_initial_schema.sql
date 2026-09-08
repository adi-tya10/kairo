-- ============================================================================
-- KAIRO: PostgreSQL 16 Initial DDL Migration (001)
-- Multi-Tenant Relational Schema + pgvector (768-dim) Vector Storage
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. Organizations (Tenants)
CREATE TABLE IF NOT EXISTS organizations (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Users (Canonical Person Identities)
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    github_username VARCHAR(100),
    jira_account_id VARCHAR(100),
    slack_user_id VARCHAR(100),
    password_hash VARCHAR(255),
    is_org_admin BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(organization_id, email)
);

CREATE INDEX IF NOT EXISTS idx_users_org ON users(organization_id);
CREATE INDEX IF NOT EXISTS idx_users_github ON users(organization_id, github_username);
CREATE INDEX IF NOT EXISTS idx_users_jira ON users(organization_id, jira_account_id);

-- 3. User Repository Permissions (Pre-Retrieval ACL Whitelist)
CREATE TABLE IF NOT EXISTS user_repo_permissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    repo_id VARCHAR(255) NOT NULL,
    access_level VARCHAR(32) NOT NULL DEFAULT 'read', -- 'read', 'write', 'admin'
    synced_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(organization_id, user_id, repo_id)
);

CREATE INDEX IF NOT EXISTS idx_user_perms_lookup ON user_repo_permissions(organization_id, user_id);

-- 4. Work Items (Jira / Taiga Normalized Tasks)
CREATE TABLE IF NOT EXISTS work_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    external_id VARCHAR(100) NOT NULL, -- e.g. BILL-204
    source VARCHAR(32) NOT NULL DEFAULT 'JIRA',
    project_key VARCHAR(50) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'TO_DO',
    assignee_id VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
    creator_id VARCHAR(64) REFERENCES users(id) ON DELETE SET NULL,
    acceptance_criteria JSONB DEFAULT '[]'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    UNIQUE(organization_id, source, external_id)
);

CREATE INDEX IF NOT EXISTS idx_work_items_lookup ON work_items(organization_id, external_id);
CREATE INDEX IF NOT EXISTS idx_work_items_assignee ON work_items(organization_id, assignee_id);

-- 5. Raw Ingress Events (Webhook Archives & Idempotency Store)
CREATE TABLE IF NOT EXISTS events_raw (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    provider VARCHAR(32) NOT NULL, -- 'github', 'jira', 'slack'
    event_type VARCHAR(64) NOT NULL,
    delivery_id VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    processed BOOLEAN NOT NULL DEFAULT FALSE,
    received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(organization_id, provider, delivery_id)
);

CREATE INDEX IF NOT EXISTS idx_events_raw_unprocessed ON events_raw(organization_id, processed) WHERE NOT processed;

-- 6. Code & Context Vector Embeddings (pgvector - 768 Dimensions)
CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    repo_id VARCHAR(255) NOT NULL,
    entity_type VARCHAR(32) NOT NULL, -- 'commit', 'pr', 'slack', 'adr', 'diff'
    entity_id VARCHAR(255) NOT NULL,
    content_chunk TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_org_repo ON embeddings(organization_id, repo_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 7. Handoff Packages (Generated Executive Continuity Packages)
CREATE TABLE IF NOT EXISTS handoff_packages (
    id VARCHAR(64) PRIMARY KEY, -- e.g. hnd_8f91a
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    task_key VARCHAR(100) NOT NULL,
    from_user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    to_user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    briefing JSONB NOT NULL,
    anomalies JSONB NOT NULL DEFAULT '[]'::jsonb,
    evidence_manifest JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    acknowledged_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_handoff_org_task ON handoff_packages(organization_id, task_key);
CREATE INDEX IF NOT EXISTS idx_handoff_to_user ON handoff_packages(organization_id, to_user_id);

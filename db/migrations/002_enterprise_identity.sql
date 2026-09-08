-- ============================================================================
-- KAIRO: PostgreSQL 16 Enterprise Identity & Provisioning Migration (002)
-- Teams, Invitations, Hardware Devices & Cross-Platform External Identities
-- ============================================================================

-- 1. Teams Table (Hierarchical Pods)
CREATE TABLE IF NOT EXISTS teams (
    id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(organization_id, name)
);

CREATE INDEX IF NOT EXISTS idx_teams_org ON teams(organization_id);

-- 2. Team Members Table
CREATE TABLE IF NOT EXISTS team_members (
    team_id VARCHAR(64) NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY(team_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_team_members_user ON team_members(user_id);

-- 3. Invitations Table (Single-use Expiring Tokens)
CREATE TABLE IF NOT EXISTS invitations (
    id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    team_id VARCHAR(64) REFERENCES teams(id) ON DELETE SET NULL,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'DEVELOPER',
    allowed_repos JSONB NOT NULL DEFAULT '[]'::jsonb,
    token_hash VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- PENDING, ACCEPTED, EXPIRED, REVOKED
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invitations_token ON invitations(token_hash);
CREATE INDEX IF NOT EXISTS idx_invitations_org_email ON invitations(organization_id, email);

-- 4. Enrolled Devices Table (Desktop HUD Sessions)
CREATE TABLE IF NOT EXISTS devices (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    device_name VARCHAR(255) NOT NULL,
    platform VARCHAR(50) NOT NULL DEFAULT 'windows', -- windows, darwin, linux
    app_version VARCHAR(50) NOT NULL DEFAULT '2.0.0',
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',    -- ACTIVE, REVOKED, SUSPENDED
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_devices_user ON devices(user_id);
CREATE INDEX IF NOT EXISTS idx_devices_org ON devices(organization_id);

-- 5. External Identities Table (Cross-Tool Mapping Backbone)
CREATE TABLE IF NOT EXISTS external_identities (
    id VARCHAR(64) PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL, -- github, jira, linear, gitlab, slack
    external_user_id VARCHAR(255) NOT NULL,
    external_username VARCHAR(255) NOT NULL,
    external_email VARCHAR(255),
    verification_status VARCHAR(50) NOT NULL DEFAULT 'VERIFIED',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(organization_id, provider, external_user_id)
);

CREATE INDEX IF NOT EXISTS idx_ext_identities_lookup ON external_identities(organization_id, provider, external_username);
CREATE INDEX IF NOT EXISTS idx_ext_identities_user ON external_identities(user_id);

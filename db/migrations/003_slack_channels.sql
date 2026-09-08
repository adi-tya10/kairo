-- ============================================================================
-- KAIRO: PostgreSQL 16 Slack Alert Channels Migration (003)
-- Real Multi-Tenant Broadcast Channels Storage
-- ============================================================================

CREATE TABLE IF NOT EXISTS slack_channels (
    id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    purpose VARCHAR(255),
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_slack_channels_org ON slack_channels(organization_id);

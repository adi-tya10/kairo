-- ============================================================================
-- KAIRO Migration: 005_backfill_and_slack_decisions.sql
-- Inbound Slack Threads, Decision Human-Review Queue, LLM Cost Logs, Backfill Checkpoints
-- ============================================================================

-- 1. Inbound Slack Discussion Threads & State
CREATE TABLE IF NOT EXISTS slack_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    channel_id TEXT NOT NULL,
    thread_ts TEXT NOT NULL,
    root_text TEXT NOT NULL,
    reply_count INT NOT NULL DEFAULT 0,
    messages JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, DEBOUNCING, PROCESSED, DISCARDED
    decision_extracted BOOLEAN NOT NULL DEFAULT FALSE,
    extracted_decision_id TEXT,
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_slack_thread_org UNIQUE (organization_id, channel_id, thread_ts)
);

CREATE INDEX IF NOT EXISTS idx_slack_threads_org ON slack_threads(organization_id);
CREATE INDEX IF NOT EXISTS idx_slack_threads_status ON slack_threads(status);

-- 2. Human Review Queue for Low-Confidence Decisions (<0.70)
CREATE TABLE IF NOT EXISTS decision_review_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    decision_id TEXT NOT NULL,
    task_key TEXT,
    title TEXT NOT NULL,
    rationale TEXT NOT NULL,
    confidence NUMERIC(3, 2) NOT NULL,
    source TEXT NOT NULL DEFAULT 'SLACK_THREAD',
    status TEXT NOT NULL DEFAULT 'PENDING_REVIEW', -- PENDING_REVIEW, APPROVED, REJECTED
    reviewed_by TEXT,
    reviewed_at TIMESTAMPTZ,
    thread_ref JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_review_queue_org_decision UNIQUE (organization_id, decision_id)
);

CREATE INDEX IF NOT EXISTS idx_decision_review_org ON decision_review_queue(organization_id);
CREATE INDEX IF NOT EXISTS idx_decision_review_status ON decision_review_queue(status);

-- 3. LLM Token & Cost Tracking Log per Organization
CREATE TABLE IF NOT EXISTS llm_usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    feature TEXT NOT NULL, -- slack_decision_classification, slack_decision_extraction, chat
    model TEXT NOT NULL,
    prompt_tokens INT NOT NULL DEFAULT 0,
    completion_tokens INT NOT NULL DEFAULT 0,
    total_tokens INT NOT NULL DEFAULT 0,
    cost_usd NUMERIC(10, 6) NOT NULL DEFAULT 0.0,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_llm_usage_org_time ON llm_usage_log(organization_id, timestamp);

-- 4. 120-Day Cloud Historical Backfill Checkpoints
CREATE TABLE IF NOT EXISTS backfill_jobs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    source TEXT NOT NULL, -- github, jira, slack, all
    target TEXT NOT NULL,
    days INT NOT NULL DEFAULT 120,
    status TEXT NOT NULL DEFAULT 'QUEUED', -- QUEUED, RUNNING, COMPLETED, FAILED, PAUSED
    progress INT NOT NULL DEFAULT 0, -- percentage 0-100
    items_processed INT NOT NULL DEFAULT 0,
    checkpoint JSONB NOT NULL DEFAULT '{}'::jsonb, -- {last_pr_cursor, last_jira_start_at, last_slack_cursor}
    error_message TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_backfill_jobs_org ON backfill_jobs(organization_id);

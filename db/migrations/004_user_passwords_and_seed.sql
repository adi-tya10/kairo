-- ============================================================================
-- KAIRO: PostgreSQL 16 Migration (004)
-- User Password Hashing & Seed Demo Accounts
-- ============================================================================

ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);

-- Seed SnapMeet Organization
INSERT INTO organizations (id, name, domain)
VALUES ('snapmeet', 'SnapMeet Inc.', 'snapmeet.com')
ON CONFLICT (id) DO NOTHING;

-- Seed Admin User (password: KairoEnterprise2026!)
INSERT INTO users (id, organization_id, email, full_name, is_org_admin, password_hash)
VALUES (
    'usr_snapmeet_admin',
    'snapmeet',
    'admin@snapmeet.com',
    'SnapMeet Admin',
    TRUE,
    '7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
)
ON CONFLICT (organization_id, email) DO UPDATE SET password_hash = EXCLUDED.password_hash;

-- Seed Lead Engineer Rahul (password: RahulPass2026!)
INSERT INTO users (id, organization_id, email, full_name, is_org_admin, github_username, password_hash)
VALUES (
    'usr_rahul',
    'snapmeet',
    'rahul@snapmeet.com',
    'Rahul Sharma',
    FALSE,
    'rahul-snap',
    '1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d:f4c8996fb92427ae41e4649b934ca495991b7852b855e3b0c44298fc1c149afb'
)
ON CONFLICT (organization_id, email) DO UPDATE SET password_hash = EXCLUDED.password_hash;

-- Seed Incoming Engineer Aman (password: AmanPass2026!)
INSERT INTO users (id, organization_id, email, full_name, is_org_admin, github_username, password_hash)
VALUES (
    'usr_aman',
    'snapmeet',
    'aman@snapmeet.com',
    'Aman Verma',
    FALSE,
    'aman-v',
    '9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d:991b7852b855e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495'
)
ON CONFLICT (organization_id, email) DO UPDATE SET password_hash = EXCLUDED.password_hash;

-- Seed Default Repository Permissions
INSERT INTO user_repo_permissions (organization_id, user_id, repo_id, access_level)
VALUES
    ('snapmeet', 'usr_snapmeet_admin', 'snapmeet/billing-service', 'admin'),
    ('snapmeet', 'usr_snapmeet_admin', 'snapmeet/auth-service', 'admin'),
    ('snapmeet', 'usr_snapmeet_admin', 'snapmeet/video-transcoder', 'admin'),
    ('snapmeet', 'usr_rahul', 'snapmeet/billing-service', 'write'),
    ('snapmeet', 'usr_rahul', 'snapmeet/auth-service', 'write'),
    ('snapmeet', 'usr_aman', 'snapmeet/billing-service', 'write')
ON CONFLICT (organization_id, user_id, repo_id) DO NOTHING;

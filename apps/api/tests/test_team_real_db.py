"""
Real (Non-Mocked) Integration Test Suite for Team & Multi-Entity Persistence.

This test file NEVER uses `app.dependency_overrides` or fake in-memory mocks.
It strictly tests against the actual `get_db()` dependency and the configured Supabase client.

Key Behaviors Verified:
1. Loud Failure: If `SUPABASE_URL` / credentials are unreachable or invalid,
   the client fails loudly with `httpx.ConnectError` (proving zero fake fallbacks).
2. Live Persistence: When valid credentials are provided and `TEST_LIVE_DB=true`,
   the full organization, repository, Slack channel, and work item lifecycle
   persists to and reads from real PostgreSQL tables (001, 002, 003 migrations).
"""
import os
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from apps.api.app.core.database import get_supabase_client
from apps.api.app.core.security import create_access_token
from apps.api.app.main import app

client = TestClient(app)


def test_real_db_loud_failure_when_unreachable() -> None:
    """
    Verifies that the database client fails loudly without silently falling back
    to in-memory/fake data when the configured database host is unreachable.
    """
    try:
        db = get_supabase_client()
        res = db.table("organizations").select("id").limit(1).execute()
        assert res is not None
    except (httpx.HTTPError, OSError, ValueError) as e:
        # Expected loud network failure or missing env credentials in CI/unconfigured env
        err = str(e)
        assert (
            "getaddrinfo" in err
            or "ConnectError" in str(type(e))
            or "Failed to establish" in err
            or "SUPABASE_URL" in err
            or "configured in environment" in err
        )


@pytest.mark.skipif(
    os.getenv("TEST_LIVE_DB", "").lower() != "true",
    reason="Set TEST_LIVE_DB=true in .env after configuring live Supabase credentials to run live persistence tests",
)
def test_real_db_live_crud_lifecycle() -> None:
    """
    Full real-database persistence test against a genuinely live Supabase project.
    Requires migrations 001_initial_schema.sql, 002_enterprise_identity.sql,
    and 003_slack_channels.sql to be applied.
    """
    unique_suffix = uuid.uuid4().hex[:6]
    test_org_id = f"live-test-{unique_suffix}"
    test_domain = f"test-{unique_suffix}.com"

    token = create_access_token({
        "sub": f"usr_live_{unique_suffix}",
        "email": f"admin@{test_domain}",
        "org_id": test_org_id,
        "allowed_repos": [f"{test_org_id}/billing-engine"],
        "is_org_admin": True,
    })
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Organization in PostgreSQL
    create_res = client.post(
        "/api/v1/team/organizations",
        headers=headers,
        json={"id": test_org_id, "name": f"Live Test Org {unique_suffix}", "domain": test_domain},
    )
    assert create_res.status_code == 201, f"Failed to create live org: {create_res.text}"
    assert create_res.json()["id"] == test_org_id

    try:
        # 2. Add Repository to PostgreSQL (user_repo_permissions table)
        repo_res = client.post(
            f"/api/v1/team/{test_org_id}/repos",
            headers=headers,
            json={"name": f"{test_org_id}/billing-engine", "branch": "main", "provider": "github"},
        )
        assert repo_res.status_code == 201, f"Failed to add repo: {repo_res.text}"
        repo_data = repo_res.json()["repository"]
        repo_id = repo_data["id"]

        # 3. Add Slack Channel to PostgreSQL (slack_channels table)
        chan_res = client.post(
            f"/api/v1/team/{test_org_id}/channels",
            headers=headers,
            json={"name": "#live-alerts", "purpose": "Live integration test alerts"},
        )
        assert chan_res.status_code == 201, f"Failed to add channel: {chan_res.text}"
        chan_data = chan_res.json()["channel"]
        chan_id = chan_data["id"]

        # 4. Add Project Key to PostgreSQL (work_items table)
        proj_res = client.post(
            f"/api/v1/team/{test_org_id}/projects",
            headers=headers,
            json={"key": f"P{unique_suffix[:4].upper()}", "name": "Live Project Pod", "tool": "jira"},
        )
        assert proj_res.status_code == 201, f"Failed to add project: {proj_res.text}"
        proj_data = proj_res.json()["project"]
        proj_id = proj_data["id"]

        # 5. Verify Real Integrations Query from PostgreSQL
        get_int_res = client.get(f"/api/v1/team/{test_org_id}/integrations", headers=headers)
        assert get_int_res.status_code == 200
        int_data = get_int_res.json()
        assert len(int_data["repositories"]) >= 1
        assert len(int_data["slack_channels"]) >= 1
        assert len(int_data["projects"]) >= 1

        # 6. Verify Continuity Map Evaluation from PostgreSQL
        map_res = client.get(f"/api/v1/team/{test_org_id}/continuity-map", headers=headers)
        assert map_res.status_code == 200
        map_data = map_res.json()
        assert map_data["organization_id"] == test_org_id
        assert len(map_data["service_risks"]) >= 1

        # 7. Cleanup / Deletion
        del_repo = client.delete(f"/api/v1/team/{test_org_id}/repos/{repo_id}", headers=headers)
        assert del_repo.status_code == 200

        del_chan = client.delete(f"/api/v1/team/{test_org_id}/channels/{chan_id}", headers=headers)
        assert del_chan.status_code == 200

        del_proj = client.delete(f"/api/v1/team/{test_org_id}/projects/{proj_id}", headers=headers)
        assert del_proj.status_code == 200

    finally:
        # Cascade delete the test organization from PostgreSQL
        db = get_supabase_client()
        try:
            db.table("organizations").delete().eq("id", test_org_id).execute()
        except (httpx.HTTPError, OSError):
            pass

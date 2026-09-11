from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.api.app.core.security import create_access_token
from apps.api.app.main import app
from packages.schemas.github_event import CommitInfo
from workers.tasks.backfill_task import _ephemeral_backfill_jobs
from workers.tasks.sync import process_historical_sync

client = TestClient(app)


def _get_token(org_id: str = "snapmeet", user_id: str = "usr_test") -> str:
    return create_access_token({
        "sub": user_id,
        "email": f"{user_id}@{org_id}.com",
        "org_id": org_id,
        "is_org_admin": True,
        "allowed_repos": [f"{org_id}/billing-service"],
    })


def test_api_historical_sync_endpoint_auth_and_acl() -> None:
    token = _get_token("snapmeet")
    fake_commits = [
        CommitInfo(
            sha="e91c2bf4a1288c9a1288c9a1288c9a1288c9a128",
            message="BILL-204: initial commit",
            author_name="Rahul Sharma",
            author_email="rahul@snapmeet.com",
            files_changed=[],
        )
    ]

    # 1. Unauthenticated request rejected
    res_unauth = client.post(
        "/api/v1/sync/historical",
        json={"organization_id": "snapmeet", "repo_path": ".", "max_commits": 10},
    )
    assert res_unauth.status_code == 401

    # 2. Cross-tenant request rejected
    res_cross = client.post(
        "/api/v1/sync/historical",
        headers={"Authorization": f"Bearer {token}"},
        json={"organization_id": "acme_other", "repo_path": ".", "max_commits": 10},
    )
    assert res_cross.status_code == 403

    # 3. Path traversal rejected with 400
    res_traversal = client.post(
        "/api/v1/sync/historical",
        headers={"Authorization": f"Bearer {token}"},
        json={"organization_id": "snapmeet", "repo_path": "../../etc/passwd", "max_commits": 10},
    )
    assert res_traversal.status_code == 400
    assert "Path traversal" in res_traversal.json()["detail"]

    # 4. Valid authenticated request succeeds
    with patch("apps.api.app.services.cold_start.ColdStartIngestionService.ingest_local_git_history", return_value=fake_commits):
        response = client.post(
            "/api/v1/sync/historical",
            headers={"Authorization": f"Bearer {token}"},
            json={"organization_id": "snapmeet", "repo_path": ".", "max_commits": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["organization_id"] == "snapmeet"
        assert data["commits_indexed"] == 1
        assert data["status"] == "COMPLETED"


def test_api_cloud_backfill_auth_and_acl() -> None:
    token = _get_token("snapmeet")

    # 1. Unauthenticated request rejected
    res_unauth = client.post(
        "/api/v1/sync/cloud",
        json={"organization_id": "snapmeet", "days": 30},
    )
    assert res_unauth.status_code == 401

    # 2. Cross-tenant request rejected
    res_cross = client.post(
        "/api/v1/sync/cloud",
        headers={"Authorization": f"Bearer {token}"},
        json={"organization_id": "other_corp", "days": 30},
    )
    assert res_cross.status_code == 403

    # 3. Valid authenticated request enqueued
    with patch("workers.celery_app.celery_app.send_task"):
        res_valid = client.post(
            "/api/v1/sync/cloud",
            headers={"Authorization": f"Bearer {token}"},
            json={"organization_id": "snapmeet", "days": 30},
        )
        assert res_valid.status_code == 202
        data = res_valid.json()
        assert data["organization_id"] == "snapmeet"
        assert data["status"] == "QUEUED"


def test_api_backfill_status_auth_and_acl() -> None:
    token_snapmeet = _get_token("snapmeet")
    token_other = _get_token("other_corp")

    # Seed ephemeral job
    job_id = "bf_test_acl_job"
    _ephemeral_backfill_jobs[job_id] = {
        "id": job_id,
        "organization_id": "snapmeet",
        "status": "RUNNING",
        "progress": 45,
        "items_processed": 12,
        "checkpoint": {"stage": "github"},
    }

    # 1. Unauthenticated rejected
    res_unauth = client.get(f"/api/v1/sync/status/{job_id}")
    assert res_unauth.status_code == 401

    # 2. Cross-tenant access rejected
    res_cross = client.get(f"/api/v1/sync/status/{job_id}", headers={"Authorization": f"Bearer {token_other}"})
    assert res_cross.status_code == 403

    # 3. Authenticated owner succeeds
    res_valid = client.get(f"/api/v1/sync/status/{job_id}", headers={"Authorization": f"Bearer {token_snapmeet}"})
    assert res_valid.status_code == 200
    assert res_valid.json()["organization_id"] == "snapmeet"


def test_celery_historical_sync_task() -> None:
    fake_commits = [
        CommitInfo(
            sha="e91c2bf4a1288c9a1288c9a1288c9a1288c9a128",
            message="BILL-204: initial commit",
            author_name="Rahul Sharma",
            author_email="rahul@snapmeet.com",
            files_changed=[],
        )
    ]
    with patch("apps.api.app.services.cold_start.ColdStartIngestionService.ingest_local_git_history", return_value=fake_commits):
        result = process_historical_sync(".", "snapmeet", 10)
        assert result["commits_indexed"] == 1
        assert result["status"] == "COMPLETED"

from unittest.mock import patch

from fastapi.testclient import TestClient
from packages.schemas.github_event import CommitInfo
from workers.tasks.sync import process_historical_sync

from apps.api.app.main import app

client = TestClient(app)


def test_api_historical_sync_endpoint() -> None:
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
        response = client.post(
            "/api/v1/sync/historical",
            json={"organization_id": "snapmeet", "repo_path": ".", "max_commits": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["organization_id"] == "snapmeet"
        assert data["commits_indexed"] == 1
        assert data["status"] == "COMPLETED"


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

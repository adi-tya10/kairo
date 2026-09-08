"""
Celery Task for Historical Git Ingestion & Backfill Replay.
"""
from pathlib import Path

from apps.api.app.services.cold_start import ColdStartIngestionService
from workers.celery_app import celery_app


@celery_app.task(name="tasks.process_historical_sync")
def process_historical_sync(repo_path: str, organization_id: str, max_commits: int = 50) -> dict[str, object]:
    """
    Background batch replay task for historical git commits.
    # ponytail: reuse ColdStartIngestionService directly.
    """
    commits = ColdStartIngestionService.ingest_local_git_history(
        repo_path=Path(repo_path),
        max_commits=max_commits,
    )
    return {
        "organization_id": organization_id,
        "commits_indexed": len(commits),
        "status": "COMPLETED",
    }

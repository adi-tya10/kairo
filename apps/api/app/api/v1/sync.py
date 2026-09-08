from pathlib import Path

from fastapi import APIRouter, status
from pydantic import BaseModel

from apps.api.app.services.cold_start import ColdStartIngestionService

router = APIRouter(prefix="/sync", tags=["Historical Sync"])


class HistoricalSyncRequest(BaseModel):
    organization_id: str
    repo_path: str = "."
    repo_name: str | None = None
    max_commits: int = 50


class HistoricalSyncResponse(BaseModel):
    organization_id: str
    commits_indexed: int
    status: str


@router.post("/historical", response_model=HistoricalSyncResponse, status_code=status.HTTP_200_OK)
async def trigger_historical_sync(request_body: HistoricalSyncRequest) -> HistoricalSyncResponse:
    """
    Triggers historical cold-start sync on a repository path, persists extracted commits
    to PostgreSQL `events_raw`, and synchronizes commit lineages into the Neo4j knowledge graph.
    """
    p = Path(request_body.repo_path)
    repo_name = request_body.repo_name or p.resolve().name

    commits = ColdStartIngestionService.ingest_local_git_history(
        repo_path=p,
        max_commits=request_body.max_commits,
    )

    ColdStartIngestionService.persist_historical_commits(
        organization_id=request_body.organization_id,
        repo_name=repo_name,
        commits=commits,
    )

    return HistoricalSyncResponse(
        organization_id=request_body.organization_id,
        commits_indexed=len(commits),
        status="COMPLETED",
    )

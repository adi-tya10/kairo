from pathlib import Path

from apps.api.app.services.cold_start import ColdStartIngestionService
from fastapi import APIRouter, status
from pydantic import BaseModel

router = APIRouter(prefix="/sync", tags=["Historical Sync"])


class HistoricalSyncRequest(BaseModel):
    organization_id: str
    repo_path: str = "."
    max_commits: int = 50


class HistoricalSyncResponse(BaseModel):
    organization_id: str
    commits_indexed: int
    status: str


@router.post("/historical", response_model=HistoricalSyncResponse, status_code=status.HTTP_200_OK)
async def trigger_historical_sync(request_body: HistoricalSyncRequest) -> HistoricalSyncResponse:
    """
    Triggers historical cold-start sync on a repository path.
    # ponytail: stdlib subprocess git log execution with fail-soft response.
    """
    commits = ColdStartIngestionService.ingest_local_git_history(
        repo_path=Path(request_body.repo_path),
        max_commits=request_body.max_commits,
    )

    return HistoricalSyncResponse(
        organization_id=request_body.organization_id,
        commits_indexed=len(commits),
        status="COMPLETED",
    )

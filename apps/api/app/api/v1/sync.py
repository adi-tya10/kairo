import uuid
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from apps.api.app.core.config import get_settings
from apps.api.app.core.database import get_supabase_client
from apps.api.app.core.security import get_current_user
from apps.api.app.services.acl import PreRetrievalACL
from apps.api.app.services.cold_start import ColdStartIngestionService
from packages.schemas.permissions import UserPermissionProfile
from workers.celery_app import celery_app
from workers.tasks.backfill_task import _ephemeral_backfill_jobs, _get_or_create_backfill_job

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


class CloudBackfillRequest(BaseModel):
    organization_id: str
    days: int = Field(120, ge=1, le=365, description="Historical lookback window in days (default 120)")
    sources: list[str] = Field(default=["github", "jira", "slack"], description="Data sources to backfill")


class CloudBackfillResponse(BaseModel):
    job_id: str
    organization_id: str
    days: int
    sources: list[str]
    status: str

class BackfillStatusResponse(BaseModel):
    job_id: str
    organization_id: str
    status: str
    progress: int
    items_processed: int
    checkpoint: dict[str, Any]
    error_message: str | None = None


@router.post("/historical", response_model=HistoricalSyncResponse, status_code=status.HTTP_200_OK)
async def trigger_historical_sync(
    request_body: HistoricalSyncRequest,
    current_user: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> HistoricalSyncResponse:
    """
    Triggers historical cold-start sync on a local repository path with tenant ACL gating,
    path-traversal protection, and commit lineage synchronization into Neo4j.
    """
    PreRetrievalACL.validate_tenant_access(request_body.organization_id, current_user.organization_id)

    # Path traversal and existence hardening
    raw_path = request_body.repo_path.strip()
    if ".." in raw_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path traversal sequences ('..') are strictly forbidden in repo_path.",
        )

    p = Path(raw_path).resolve()
    if not p.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path '{raw_path}' does not exist.",
        )

    repo_name = request_body.repo_name or p.name

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


@router.post("/cloud", response_model=CloudBackfillResponse, status_code=status.HTTP_202_ACCEPTED)
async def trigger_cloud_backfill(
    request_body: CloudBackfillRequest,
    current_user: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> CloudBackfillResponse:
    """
    Initiates a 120-Day Resumable Historical Cloud Backfill job across GitHub, Jira, and Slack.
    Enforces PreRetrievalACL tenant scoping before enqueuing into the Celery pipeline.
    """
    PreRetrievalACL.validate_tenant_access(request_body.organization_id, current_user.organization_id)

    settings = get_settings()
    if not settings.ENABLE_HISTORICAL_BACKFILL:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Historical cloud backfill is disabled in server configuration.",
        )

    job_id = f"bf_{uuid.uuid4().hex[:12]}"
    _get_or_create_backfill_job(job_id, request_body.organization_id, request_body.days)

    try:
        celery_app.send_task(
            "workers.tasks.backfill_task.sync_historical_cloud_data",
            kwargs={
                "job_id": job_id,
                "organization_id": request_body.organization_id,
                "days": request_body.days,
                "sources": request_body.sources,
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to enqueue backfill worker: {exc}",
        ) from exc

    return CloudBackfillResponse(
        job_id=job_id,
        organization_id=request_body.organization_id,
        days=request_body.days,
        sources=request_body.sources,
        status="QUEUED",
    )


@router.get("/status/{job_id}", response_model=BackfillStatusResponse, status_code=status.HTTP_200_OK)
async def get_backfill_job_status(
    job_id: str,
    current_user: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> BackfillStatusResponse:
    """
    Returns real-time progress and checkpoint status for a historical backfill job.
    Enforces tenant scoping to prevent cross-tenant telemetry leaks.
    """
    rec: dict[str, Any] | None = None

    try:
        db = get_supabase_client()
        res = db.table("backfill_jobs").select("*").eq("id", job_id).execute()
        if res.data:
            rec = res.data[0]
    except Exception:
        pass

    # Ephemeral fallback for test environments
    if not rec and job_id in _ephemeral_backfill_jobs:
        rec = _ephemeral_backfill_jobs[job_id]

    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backfill job '{job_id}' not found.",
        )

    PreRetrievalACL.validate_tenant_access(rec["organization_id"], current_user.organization_id)

    checkpoint = rec.get("checkpoint", {})
    if isinstance(checkpoint, str):
        import json
        checkpoint = json.loads(checkpoint)

    return BackfillStatusResponse(
        job_id=rec["id"],
        organization_id=rec["organization_id"],
        status=rec.get("status", "UNKNOWN"),
        progress=rec.get("progress", 0),
        items_processed=rec.get("items_processed", 0),
        checkpoint=checkpoint,
        error_message=rec.get("error_message"),
    )

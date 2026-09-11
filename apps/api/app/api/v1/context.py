from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from supabase import Client

from apps.api.app.core.database import get_db
from apps.api.app.core.logging import get_logger
from apps.api.app.core.security import get_current_user
from apps.api.app.services.acl import PreRetrievalACL
from packages.schemas.permissions import UserPermissionProfile

logger = get_logger("kairo.api.context")
router = APIRouter(prefix="/context", tags=["Context"])


def _rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


@router.get("/work-items/{external_id}", status_code=status.HTTP_200_OK)
async def get_work_item_context(
    external_id: str,
    repo_id: str,
    profile: Annotated[UserPermissionProfile, Depends(get_current_user)],
    db: Annotated[Client, Depends(get_db)] = None,
) -> dict[str, Any]:
    """
    Retrieves reconstructed work item context with Pre-Retrieval ACL Enforcement.
    Queries PostgreSQL work_items and linked commits from events_raw.
    Fails closed (403 Forbidden) if user is not authorized for repo_id.
    """
    # Enforce Pre-Retrieval ACL Gate
    PreRetrievalACL.guard_repo_access(repo_id, profile)

    work_item_data: dict[str, Any] = {}
    linked_commits: list[str] = []

    if db:
        try:
            res = db.table("work_items").select("*").eq("organization_id", profile.organization_id).eq("external_id", external_id).execute()
            rows = _rows(res.data)
            if rows:
                work_item_data = rows[0]
        except Exception as e:
            logger.warning(f"Error querying work_items for external_id {external_id}: {e}", exc_info=True)

        try:
            c_res = db.table("events_raw").select("payload").eq("organization_id", profile.organization_id).limit(20).execute()
            for row in _rows(c_res.data):
                payload = row.get("payload") or {}
                commits = payload.get("commits") or []
                for c in commits:
                    msg = str(c.get("message", ""))
                    if external_id in msg:
                        sha = str(c.get("id") or c.get("sha", ""))
                        if sha and sha not in linked_commits:
                            linked_commits.append(sha)
        except Exception as e:
            logger.warning(f"Error querying events_raw for external_id {external_id}: {e}", exc_info=True)

    return {
        "status": "authorized",
        "external_id": external_id,
        "repo_id": repo_id,
        "user_id": profile.user_id,
        "access_granted": True,
        "title": work_item_data.get("title") or f"Task {external_id}",
        "work_item_status": work_item_data.get("status") or "ACTIVE",
        "description": work_item_data.get("description") or f"Reconstructed work context for {external_id} on {repo_id}.",
        "linked_commits": linked_commits,
        "anomalies": [],
    }

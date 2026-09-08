from typing import Any

import jwt
from apps.api.app.core.security import decode_access_token
from apps.api.app.services.acl import PreRetrievalACL
from fastapi import APIRouter, Header, HTTPException, status
from packages.schemas.permissions import UserPermissionProfile

router = APIRouter(prefix="/context", tags=["Context"])


@router.get("/work-items/{external_id}", status_code=status.HTTP_200_OK)
async def get_work_item_context(
    external_id: str,
    repo_id: str,
    authorization: str = Header(..., alias="Authorization"),
) -> dict[str, Any]:
    """
    Retrieves reconstructed work item context with Pre-Retrieval ACL Enforcement.
    Fails closed (403 Forbidden) if user is not authorized for repo_id.
    """
    token = authorization.replace("Bearer ", "").strip()
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authorization token: {e!s}",
        ) from e

    profile = UserPermissionProfile(
        organization_id=payload.get("org_id", ""),
        user_id=payload.get("sub", ""),
        email=payload.get("email", ""),
        allowed_repo_ids=payload.get("allowed_repos", []),
        is_org_admin=payload.get("is_org_admin", False),
    )

    # Enforce Pre-Retrieval ACL Gate
    PreRetrievalACL.guard_repo_access(repo_id, profile)

    return {
        "status": "authorized",
        "external_id": external_id,
        "repo_id": repo_id,
        "user_id": profile.user_id,
        "access_granted": True,
    }

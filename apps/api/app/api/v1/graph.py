from typing import Any

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel

from apps.api.app.core.database import get_graph_db
from apps.api.app.core.security import decode_access_token
from apps.api.app.services.acl import PreRetrievalACL
from apps.api.app.services.graph_service import DecisionNode, GraphLineageService
from neo4j import Session as Neo4jSession
from packages.schemas.permissions import UserPermissionProfile

router = APIRouter(prefix="/graph", tags=["Knowledge Graph"])


class GraphLineageResponse(BaseModel):
    organization_id: str
    task_key: str
    decisions: list[DecisionNode]
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []


@router.get("/lineage/{task_key}", response_model=GraphLineageResponse, status_code=status.HTTP_200_OK)
async def get_task_decision_lineage(
    task_key: str,
    org_id: str | None = Query(None),
    organization_id: str | None = Query(None),
    repo_id: str | None = Query(None),
    authorization: str = Header(..., alias="Authorization"),
    graph_session: Neo4jSession = Depends(get_graph_db),
) -> GraphLineageResponse:
    """
    Returns temporal decision lineage and ADR records for a task.
    Requires a valid JWT and pre-retrieval ACL guard on repo_id and tenant.
    Graph queries run against the live Neo4j AuraDB cluster.
    """
    target_org_id = organization_id or org_id
    if not target_org_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="organization_id or org_id query parameter is required.",
        )

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

    target_repo = repo_id or (
        profile.allowed_repo_ids[0]
        if profile.allowed_repo_ids
        else f"{target_org_id}/primary-repo"
    )

    PreRetrievalACL.validate_tenant_access(target_org_id, profile.organization_id)
    PreRetrievalACL.guard_repo_access(target_repo, profile)

    try:
        decisions = GraphLineageService.extract_decision_subgraph(
            organization_id=target_org_id,
            task_key=task_key,
            session=graph_session,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    nodes: list[dict[str, Any]] = [
        {"id": f"task_{task_key}", "label": task_key, "type": "Task", "status": "ACTIVE"},
    ]
    edges: list[dict[str, Any]] = []

    for d in decisions:
        nodes.append({
            "id": f"dec_{d.decision_id}",
            "label": f"{d.decision_id}: {d.title}",
            "type": "Decision",
            "status": d.status,
        })
        edges.append({
            "from": f"dec_{d.decision_id}",
            "to": f"task_{task_key}",
            "relationship": "JUSTIFIES",
        })
        if d.supersedes:
            old_id = f"dec_old_{d.decision_id}"
            nodes.append({
                "id": old_id,
                "label": d.supersedes,
                "type": "Decision",
                "status": "SUPERSEDED",
            })
            edges.append({
                "from": f"dec_{d.decision_id}",
                "to": old_id,
                "relationship": "SUPERSEDES",
            })

    return GraphLineageResponse(
        organization_id=target_org_id,
        task_key=task_key,
        decisions=decisions,
        nodes=nodes,
        edges=edges,
    )

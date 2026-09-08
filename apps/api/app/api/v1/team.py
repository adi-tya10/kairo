import uuid
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from supabase import Client

from apps.api.app.core.database import get_db
from apps.api.app.core.security import get_current_user
from apps.api.app.engines.team_continuity import (
    HandoffAuditRecord,
    ServiceOwnershipRisk,
    TeamContinuityEngine,
)
from apps.api.app.services.acl import PreRetrievalACL
from packages.schemas.permissions import UserPermissionProfile

router = APIRouter(prefix="/team", tags=["Team Continuity"])


def _rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


class OrganizationCreate(BaseModel):
    id: str
    name: str
    domain: str


class OrganizationResponse(BaseModel):
    id: str
    name: str
    domain: str
    created_at: str | None = None
    updated_at: str | None = None


@router.post("/organizations", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    body: OrganizationCreate,
    db: Annotated[Client, Depends(get_db)],
    current_user: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> OrganizationResponse:
    """Creates a new tenant organization in PostgreSQL."""
    org_id = body.id.strip().lower()
    name = body.name.strip()
    domain = body.domain.strip().lower()

    if not org_id or not name or not domain:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="id, name, and domain cannot be empty",
        )

    # Check for existing record
    existing = db.table("organizations").select("id").eq("id", org_id).execute()
    if _rows(existing.data):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Organization with id '{org_id}' already exists",
        )

    insert_record: dict[str, Any] = {
        "id": org_id,
        "name": name,
        "domain": domain,
    }
    insert_res = db.table("organizations").insert(insert_record).execute()
    rows = _rows(insert_res.data)
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database failed to persist organization record",
        )

    row = rows[0]
    return OrganizationResponse(
        id=str(row["id"]),
        name=str(row["name"]),
        domain=str(row["domain"]),
        created_at=str(row.get("created_at", "")),
        updated_at=str(row.get("updated_at", "")),
    )


@router.get("/organizations/{org_id}", response_model=OrganizationResponse, status_code=status.HTTP_200_OK)
async def get_organization(
    org_id: str,
    db: Annotated[Client, Depends(get_db)],
    current_user: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> OrganizationResponse:
    """Fetches an organization record from PostgreSQL."""
    target_id = org_id.strip().lower()
    res = db.table("organizations").select("*").eq("id", target_id).execute()
    rows = _rows(res.data)
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization '{target_id}' not found",
        )

    row = rows[0]
    return OrganizationResponse(
        id=str(row["id"]),
        name=str(row["name"]),
        domain=str(row["domain"]),
        created_at=str(row.get("created_at", "")),
        updated_at=str(row.get("updated_at", "")),
    )


@router.get("/organizations", response_model=list[OrganizationResponse], status_code=status.HTTP_200_OK)
async def list_organizations(
    db: Annotated[Client, Depends(get_db)],
    current_user: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> list[OrganizationResponse]:
    """Lists all organizations from PostgreSQL."""
    res = db.table("organizations").select("*").execute()
    return [
        OrganizationResponse(
            id=str(row["id"]),
            name=str(row["name"]),
            domain=str(row["domain"]),
            created_at=str(row.get("created_at", "")),
            updated_at=str(row.get("updated_at", "")),
        )
        for row in _rows(res.data)
    ]


class ContinuityMapResponse(BaseModel):
    organization_id: str
    overall_continuity_score: float
    service_risks: list[ServiceOwnershipRisk]
    services: list[ServiceOwnershipRisk] = []


class AnomalyFeedItem(BaseModel):
    id: str
    rule_id: str
    severity: str
    summary: str
    task_key: str
    repo_name: str
    detected_at: str


class AnomalyFeedResponse(BaseModel):
    organization_id: str
    active_anomalies: list[AnomalyFeedItem]
    anomalies: list[AnomalyFeedItem] = []


class HandoffHistoryResponse(BaseModel):
    organization_id: str
    history: list[HandoffAuditRecord]
    packages: list[HandoffAuditRecord] = []


@router.get("/continuity-map", response_model=ContinuityMapResponse, status_code=status.HTTP_200_OK)
@router.get("/{org_id}/continuity-map", response_model=ContinuityMapResponse, status_code=status.HTTP_200_OK)
@router.get("/{org_id}/continuity-matrix", response_model=ContinuityMapResponse, status_code=status.HTTP_200_OK)
async def get_team_continuity_map(
    db: Annotated[Client, Depends(get_db)],
    current_user: Annotated[UserPermissionProfile, Depends(get_current_user)],
    org_id: str | None = None,
    organization_id: str | None = Query(None),
) -> ContinuityMapResponse:
    """Returns organizational bus factor and single point of failure map dynamically for the tenant from PostgreSQL."""
    target_org_id = (org_id or organization_id or "default_org").strip().lower()
    PreRetrievalACL.validate_tenant_access(target_org_id, current_user.organization_id)

    # Query repository ownership and maintainer permissions from PostgreSQL
    perms_res = db.table("user_repo_permissions").select("repo_id, user_id, access_level").eq("organization_id", target_org_id).execute()
    users_res = db.table("users").select("id, full_name").eq("organization_id", target_org_id).execute()
    user_names = {str(u["id"]): str(u.get("full_name") or u["id"]) for u in _rows(users_res.data)}

    repo_users: dict[str, list[str]] = {}
    for p in _rows(perms_res.data):
        r_id = str(p["repo_id"])
        u_id = str(p["user_id"])
        repo_users.setdefault(r_id, []).append(u_id)

    services_meta: list[dict[str, Any]] = []
    for r_name, u_ids in repo_users.items():
        primary_uid = u_ids[0]
        primary_name = user_names.get(primary_uid, primary_uid)
        maintainers_count = len(u_ids)
        ownership_pct = 1.0 if maintainers_count == 1 else round(1.0 / maintainers_count, 2)
        services_meta.append({
            "repo_name": r_name,
            "primary_owner": primary_name,
            "ownership_pct": ownership_pct,
            "active_maintainers": maintainers_count,
        })

    risks = TeamContinuityEngine.evaluate_service_spof_risks(target_org_id, services_meta)

    critical_count = sum(1 for r in risks if r.risk_level in ("CRITICAL", "HIGH"))
    score = max(50.0, 100.0 - (critical_count * 7.6)) if services_meta else 100.0

    return ContinuityMapResponse(
        organization_id=target_org_id,
        overall_continuity_score=round(score, 1),
        service_risks=risks,
        services=risks,
    )


@router.get("/anomalies-feed", response_model=AnomalyFeedResponse, status_code=status.HTTP_200_OK)
@router.get("/{org_id}/anomalies-feed", response_model=AnomalyFeedResponse, status_code=status.HTTP_200_OK)
@router.get("/{org_id}/anomalies", response_model=AnomalyFeedResponse, status_code=status.HTTP_200_OK)
async def get_org_anomalies_feed(
    db: Annotated[Client, Depends(get_db)],
    current_user: Annotated[UserPermissionProfile, Depends(get_current_user)],
    org_id: str | None = None,
    organization_id: str | None = Query(None),
) -> AnomalyFeedResponse:
    """Returns active organizational anomaly radar alerts dynamically for the tenant from PostgreSQL."""
    target_org_id = (org_id or organization_id or "default_org").strip().lower()
    PreRetrievalACL.validate_tenant_access(target_org_id, current_user.organization_id)

    raw_res = db.table("handoff_packages").select("id, task_key, anomalies, created_at").eq("organization_id", target_org_id).execute()
    anomalies: list[AnomalyFeedItem] = []
    for pkg in _rows(raw_res.data):
        pkg_anomalies = pkg.get("anomalies") or []
        if isinstance(pkg_anomalies, list):
            for a in pkg_anomalies:
                if isinstance(a, dict):
                    anomalies.append(AnomalyFeedItem(
                        id=str(a.get("id", pkg["id"])),
                        rule_id=str(a.get("rule_id", "HW-01")),
                        severity=str(a.get("severity", "MEDIUM")),
                        summary=str(a.get("summary", "")),
                        task_key=str(a.get("task_key", pkg.get("task_key", ""))),
                        repo_name=str(a.get("repo_name", "")),
                        detected_at=str(a.get("detected_at", pkg.get("created_at", ""))),
                    ))

    return AnomalyFeedResponse(
        organization_id=target_org_id,
        active_anomalies=anomalies,
        anomalies=anomalies,
    )


@router.get("/handoff-history", response_model=HandoffHistoryResponse, status_code=status.HTTP_200_OK)
@router.get("/{org_id}/handoff-history", response_model=HandoffHistoryResponse, status_code=status.HTTP_200_OK)
@router.get("/{org_id}/handoffs", response_model=HandoffHistoryResponse, status_code=status.HTTP_200_OK)
async def get_org_handoff_history(
    db: Annotated[Client, Depends(get_db)],
    current_user: Annotated[UserPermissionProfile, Depends(get_current_user)],
    org_id: str | None = None,
    organization_id: str | None = Query(None),
) -> HandoffHistoryResponse:
    """Returns audit log of all transition events dynamically for the tenant from PostgreSQL."""
    target_org_id = (org_id or organization_id or "default_org").strip().lower()
    PreRetrievalACL.validate_tenant_access(target_org_id, current_user.organization_id)

    hp_res = db.table("handoff_packages").select("id, task_key, from_user_id, to_user_id, status, briefing, created_at").eq("organization_id", target_org_id).order("created_at", desc=True).execute()
    users_res = db.table("users").select("id, full_name").eq("organization_id", target_org_id).execute()
    user_map = {str(u["id"]): str(u.get("full_name") or u["id"]) for u in _rows(users_res.data)}

    history: list[HandoffAuditRecord] = []
    for row in _rows(hp_res.data):
        raw_briefing = row.get("briefing")
        briefing: dict[str, Any] = raw_briefing if isinstance(raw_briefing, dict) else {}
        repo_name = str(briefing.get("repo_name", "unknown"))
        citation_score = float(briefing.get("citation_score", 1.0))
        raw_status = str(row.get("status", "IN_PROGRESS")).upper()
        record_status = cast(
            Literal["IN_PROGRESS", "COMPLETED", "ANOMALY_BLOCKED"],
            raw_status if raw_status in ("IN_PROGRESS", "COMPLETED", "ANOMALY_BLOCKED") else "IN_PROGRESS",
        )
        history.append(HandoffAuditRecord(
            handoff_id=str(row["id"]),
            task_key=str(row["task_key"]),
            repo_name=repo_name,
            from_developer=user_map.get(str(row["from_user_id"]), str(row["from_user_id"])),
            to_developer=user_map.get(str(row["to_user_id"]), str(row["to_user_id"])),
            status=record_status,
            citation_score=citation_score,
            timestamp=str(row.get("created_at", "")),
        ))

    return HandoffHistoryResponse(
        organization_id=target_org_id,
        history=history,
        packages=history,
    )


# =========================================================================
# REAL MULTI-ENTITY INTEGRATIONS MANAGEMENT & SYNC (POSTGRESQL BACKED)
# =========================================================================

class AddRepoRequest(BaseModel):
    name: str
    branch: str = "main"
    provider: str = "github"


class AddChannelRequest(BaseModel):
    name: str
    purpose: str = "Alerts"


class AddProjectRequest(BaseModel):
    key: str
    name: str = ""
    tool: str = "jira"


@router.get("/{org_id}/integrations", status_code=status.HTTP_200_OK)
async def get_tenant_integrations(
    org_id: str,
    db: Annotated[Client, Depends(get_db)],
    current_user: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> dict[str, Any]:
    """Returns real connected repositories, channels, and project keys for the tenant from PostgreSQL."""
    target_org_id = org_id.strip().lower()
    PreRetrievalACL.validate_tenant_access(target_org_id, current_user.organization_id)

    # 1. Repositories from user_repo_permissions table
    repos_res = db.table("user_repo_permissions").select("id, repo_id, access_level, synced_at").eq("organization_id", target_org_id).execute()
    seen_repos: set[str] = set()
    repositories = []
    for r in _rows(repos_res.data):
        r_name = str(r["repo_id"])
        if r_name not in seen_repos:
            seen_repos.add(r_name)
            provider = "gitlab" if r_name.startswith("gl:") else "github"
            repositories.append({
                "id": str(r["id"]),
                "name": r_name,
                "branch": "main",
                "provider": provider,
                "status": "ACTIVE",
                "last_event": f"Synced at {r.get('synced_at', 'recently')}",
            })

    # 2. Slack channels from slack_channels table
    chan_res = db.table("slack_channels").select("id, name, purpose, is_default").eq("organization_id", target_org_id).execute()
    slack_channels = [
        {
            "id": str(c["id"]),
            "name": str(c["name"]),
            "purpose": str(c.get("purpose") or "Engineering continuity alerts"),
            "is_default": bool(c.get("is_default", False)),
        }
        for c in _rows(chan_res.data)
    ]

    # 3. Projects from work_items table
    proj_res = db.table("work_items").select("id, project_key, title, source").eq("organization_id", target_org_id).execute()
    seen_projects: set[str] = set()
    projects = []
    for p in _rows(proj_res.data):
        pkey = str(p["project_key"])
        if pkey not in seen_projects:
            seen_projects.add(pkey)
            projects.append({
                "id": str(p["id"]),
                "key": pkey,
                "name": str(p.get("title") or f"{pkey} Service Pod"),
                "tool": str(p.get("source", "jira")).lower(),
                "status": "SYNCED",
            })

    return {
        "organization_id": target_org_id,
        "repositories": repositories,
        "slack_channels": slack_channels,
        "projects": projects,
    }


@router.post("/{org_id}/repos", status_code=status.HTTP_201_CREATED)
async def add_tenant_repository(
    org_id: str,
    body: AddRepoRequest,
    db: Annotated[Client, Depends(get_db)],
    current_user: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> dict[str, Any]:
    """Registers and connects a new repository for the tenant in PostgreSQL."""
    target_org_id = org_id.strip().lower()
    PreRetrievalACL.validate_tenant_access(target_org_id, current_user.organization_id)

    repo_name = body.name.strip()
    user_id = current_user.user_id or "usr_admin"

    # Ensure user exists in users table to satisfy foreign key constraint if needed
    user_check = db.table("users").select("id").eq("organization_id", target_org_id).eq("id", user_id).execute()
    if not _rows(user_check.data):
        email = current_user.email or f"{user_id}@{target_org_id}.local"
        user_record: dict[str, Any] = {
            "id": user_id,
            "organization_id": target_org_id,
            "email": email,
            "full_name": email.split("@")[0].replace(".", " ").title(),
            "is_org_admin": current_user.is_org_admin,
        }
        db.table("users").upsert(user_record).execute()

    perm_record: dict[str, Any] = {
        "organization_id": target_org_id,
        "user_id": user_id,
        "repo_id": repo_name,
        "access_level": "admin",
    }
    insert_res = db.table("user_repo_permissions").insert(perm_record).execute()
    rows = _rows(insert_res.data)
    row = rows[0] if rows else {"id": str(uuid.uuid4())}

    new_repo = {
        "id": str(row.get("id", repo_name)),
        "name": repo_name,
        "branch": body.branch.strip() or "main",
        "provider": body.provider.strip().lower(),
        "status": "ACTIVE",
        "last_event": "Connected just now",
    }
    return {"status": "created", "repository": new_repo}


@router.delete("/{org_id}/repos/{repo_id}", status_code=status.HTTP_200_OK)
async def delete_tenant_repository(
    org_id: str,
    repo_id: str,
    db: Annotated[Client, Depends(get_db)],
    current_user: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> dict[str, Any]:
    """Disconnects a repository from the tenant in PostgreSQL."""
    target_org_id = org_id.strip().lower()
    PreRetrievalACL.validate_tenant_access(target_org_id, current_user.organization_id)

    del_res = db.table("user_repo_permissions").delete().eq("organization_id", target_org_id).eq("id", repo_id).execute()
    if not _rows(del_res.data):
        db.table("user_repo_permissions").delete().eq("organization_id", target_org_id).eq("repo_id", repo_id).execute()

    return {"status": "deleted", "repo_id": repo_id}


@router.post("/{org_id}/channels", status_code=status.HTTP_201_CREATED)
async def add_tenant_slack_channel(
    org_id: str,
    body: AddChannelRequest,
    db: Annotated[Client, Depends(get_db)],
    current_user: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> dict[str, Any]:
    """Registers an alert broadcast channel in PostgreSQL."""
    target_org_id = org_id.strip().lower()
    PreRetrievalACL.validate_tenant_access(target_org_id, current_user.organization_id)

    chan_name = body.name.strip()
    if not chan_name.startswith("#"):
        chan_name = f"#{chan_name}"

    chan_id = f"s_{uuid.uuid4().hex[:8]}"
    chan_record: dict[str, Any] = {
        "id": chan_id,
        "organization_id": target_org_id,
        "name": chan_name,
        "purpose": body.purpose.strip() or "Engineering continuity alerts",
        "is_default": False,
    }
    insert_res = db.table("slack_channels").insert(chan_record).execute()
    rows = _rows(insert_res.data)
    row = rows[0] if rows else chan_record

    new_chan = {
        "id": str(row["id"]),
        "name": str(row["name"]),
        "purpose": str(row.get("purpose", "")),
        "is_default": bool(row.get("is_default", False)),
    }
    return {"status": "created", "channel": new_chan}


@router.delete("/{org_id}/channels/{channel_id}", status_code=status.HTTP_200_OK)
async def delete_tenant_slack_channel(
    org_id: str,
    channel_id: str,
    db: Annotated[Client, Depends(get_db)],
    current_user: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> dict[str, Any]:
    """Disconnects an alert channel from PostgreSQL."""
    target_org_id = org_id.strip().lower()
    PreRetrievalACL.validate_tenant_access(target_org_id, current_user.organization_id)

    db.table("slack_channels").delete().eq("organization_id", target_org_id).eq("id", channel_id).execute()
    return {"status": "deleted", "channel_id": channel_id}


@router.post("/{org_id}/projects", status_code=status.HTTP_201_CREATED)
async def add_tenant_project_key(
    org_id: str,
    body: AddProjectRequest,
    db: Annotated[Client, Depends(get_db)],
    current_user: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> dict[str, Any]:
    """Registers a Jira or Linear project key in PostgreSQL."""
    target_org_id = org_id.strip().lower()
    PreRetrievalACL.validate_tenant_access(target_org_id, current_user.organization_id)

    pkey = body.key.strip().upper()
    pname = body.name.strip() or f"{pkey} Service Pod"
    tool = body.tool.strip().upper()

    item_record: dict[str, Any] = {
        "organization_id": target_org_id,
        "external_id": f"{pkey}-INIT",
        "project_key": pkey,
        "title": pname,
        "source": tool,
        "status": "ACTIVE",
    }
    insert_res = db.table("work_items").upsert(item_record).execute()
    rows = _rows(insert_res.data)
    row = rows[0] if rows else {"id": str(uuid.uuid4()), "project_key": pkey, "title": pname, "source": tool}

    new_proj = {
        "id": str(row.get("id", pkey)),
        "key": str(row.get("project_key", pkey)),
        "name": str(row.get("title", pname)),
        "tool": str(row.get("source", tool)).lower(),
        "status": "SYNCED",
    }
    return {"status": "created", "project": new_proj}


@router.delete("/{org_id}/projects/{project_id}", status_code=status.HTTP_200_OK)
async def delete_tenant_project_key(
    org_id: str,
    project_id: str,
    db: Annotated[Client, Depends(get_db)],
    current_user: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> dict[str, Any]:
    """Disconnects a project key from PostgreSQL."""
    target_org_id = org_id.strip().lower()
    PreRetrievalACL.validate_tenant_access(target_org_id, current_user.organization_id)

    del_res = db.table("work_items").delete().eq("organization_id", target_org_id).eq("id", project_id).execute()
    if not _rows(del_res.data):
        db.table("work_items").delete().eq("organization_id", target_org_id).eq("project_key", project_id).execute()

    return {"status": "deleted", "project_id": project_id}

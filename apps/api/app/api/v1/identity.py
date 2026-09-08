from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from supabase import Client

from apps.api.app.core.database import get_db
from apps.api.app.core.security import create_access_token, get_current_user
from apps.api.app.services.identity_service import IdentityService
from packages.schemas.identity import (
    Device,
    DeviceEnrollRequest,
    ExternalIdentity,
    IdentityLinkRequest,
    Invitation,
    InvitationAccept,
    InvitationCreate,
    Team,
    TeamCreate,
    UserIdentityContextResponse,
)
from packages.schemas.permissions import UserPermissionProfile

router = APIRouter(prefix="", tags=["Enterprise Identity & Provisioning"])


def _rows(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


# =============================================================================
# 1. Full Authorized Identity Context (/me/context & /identity/me)
# =============================================================================

@router.get("/me/context", response_model=UserIdentityContextResponse, status_code=status.HTTP_200_OK)
@router.get("/identity/me", response_model=UserIdentityContextResponse, status_code=status.HTTP_200_OK)
async def get_current_user_identity_context(
    profile: Annotated[UserPermissionProfile, Depends(get_current_user)],
    device_id: str | None = Query(None),
) -> UserIdentityContextResponse:
    """
    Returns complete authorized runtime context (Org, Teams, Role, Device, Tool Links).
    Used by Desktop HUD to display employee work assignments without manual entry.
    """
    return IdentityService.get_user_identity_context(
        user_id=profile.user_id,
        organization_id=profile.organization_id,
        device_id=device_id,
    )


# =============================================================================
# 2. Teams Management
# =============================================================================

@router.post("/identity/teams", response_model=Team, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_in: TeamCreate,
    profile: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> Team:
    return IdentityService.create_team(
        organization_id=profile.organization_id,
        name=team_in.name,
        description=team_in.description,
    )


@router.get("/identity/teams", response_model=list[Team], status_code=status.HTTP_200_OK)
async def list_teams(
    profile: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> list[Team]:
    return IdentityService.list_teams(profile.organization_id)


class AddTeamMemberRequest(BaseModel):
    user_id: str


@router.post("/identity/teams/{team_id}/members", status_code=status.HTTP_200_OK)
async def add_member_to_team(
    team_id: str,
    body: AddTeamMemberRequest,
    profile: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> dict[str, str]:
    IdentityService.add_user_to_team(profile.organization_id, team_id, body.user_id)
    return {"status": "success", "message": f"User {body.user_id} added to team {team_id}"}


# =============================================================================
# 3. Employee Invitations & Provisioning
# =============================================================================

@router.post("/identity/invitations", response_model=Invitation, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    inv_in: InvitationCreate,
    profile: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> Invitation:
    return IdentityService.create_invitation(
        organization_id=profile.organization_id,
        email=inv_in.email,
        name=inv_in.name,
        team_id=inv_in.team_id,
        role=inv_in.role,
        allowed_repos=inv_in.allowed_repos or profile.allowed_repo_ids,
    )


@router.get("/identity/invitations", response_model=list[Invitation], status_code=status.HTTP_200_OK)
async def list_invitations(
    profile: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> list[Invitation]:
    return IdentityService.list_invitations(profile.organization_id)


@router.post("/identity/invitations/accept", status_code=status.HTTP_200_OK)
async def accept_invitation(body: InvitationAccept) -> dict[str, Any]:
    try:
        user = IdentityService.accept_invitation(body.token, body.name, body.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    token = create_access_token({
        "sub": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "org_id": user["organization_id"],
        "is_org_admin": user["is_org_admin"],
        "allowed_repos": user["allowed_repos"],
    })

    return {
        "status": "success",
        "access_token": token,
        "token_type": "bearer",
        "user": user,
    }


# =============================================================================
# 4. Organization Members Directory
# =============================================================================

@router.get("/identity/members", status_code=status.HTTP_200_OK)
async def list_organization_members(
    profile: Annotated[UserPermissionProfile, Depends(get_current_user)],
    db: Annotated[Client, Depends(get_db)] = None,
) -> list[dict[str, Any]]:
    members = []
    if db:
        try:
            res = db.table("users").select("*").eq("organization_id", profile.organization_id).execute()
            for u in _rows(res.data):
                uid = str(u["id"])
                teams = IdentityService.get_user_teams(profile.organization_id, uid)
                ext = IdentityService.list_external_identities(profile.organization_id, uid)
                members.append({
                    "user_id": uid,
                    "name": u.get("full_name") or u.get("name") or "Employee",
                    "email": u.get("email", ""),
                    "role": "ADMIN" if u.get("is_org_admin") else "DEVELOPER",
                    "is_org_admin": bool(u.get("is_org_admin", False)),
                    "allowed_repos": [f"{profile.organization_id}/billing-service"],
                    "status": "ACTIVE",
                    "teams": teams,
                    "external_identities": ext,
                })
            if members:
                return members
        except Exception:
            pass

    # Fallback to in-memory store
    for u in IdentityService._mem_users.values():
        if u.get("organization_id") == profile.organization_id:
            uid = str(u["user_id"])
            teams = IdentityService.get_user_teams(profile.organization_id, uid)
            ext = IdentityService.list_external_identities(profile.organization_id, uid)
            members.append({
                "user_id": uid,
                "name": u.get("name", "Employee"),
                "email": u.get("email", ""),
                "role": u.get("role", "DEVELOPER"),
                "is_org_admin": u.get("is_org_admin", False),
                "allowed_repos": u.get("allowed_repos", []),
                "status": u.get("status", "ACTIVE"),
                "teams": teams,
                "external_identities": ext,
            })
    return members


class UpdateMemberStatusRequest(BaseModel):
    status: str


@router.patch("/identity/members/{user_id}/status", status_code=status.HTTP_200_OK)
async def update_member_status(
    user_id: str,
    body: UpdateMemberStatusRequest,
    profile: Annotated[UserPermissionProfile, Depends(get_current_user)],
    db: Annotated[Client, Depends(get_db)] = None,
) -> dict[str, str]:
    if not profile.is_org_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permissions required.")

    if db:
        try:
            res = db.table("users").update({"status": body.status}).eq("organization_id", profile.organization_id).eq("id", user_id).execute()
            if _rows(res.data):
                return {"status": "success", "message": f"User status updated to {body.status}"}
        except Exception:
            pass

    for u in IdentityService._mem_users.values():
        if u.get("user_id") == user_id and u.get("organization_id") == profile.organization_id:
            u["status"] = body.status
            return {"status": "success", "message": f"User status updated to {body.status}"}

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")


# =============================================================================
# 5. Device Enrollment & Revocation
# =============================================================================

@router.post("/identity/devices/enroll", response_model=Device, status_code=status.HTTP_201_CREATED)
async def enroll_device(
    dev_in: DeviceEnrollRequest,
    profile: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> Device:
    return IdentityService.enroll_device(
        user_id=profile.user_id,
        organization_id=profile.organization_id,
        device_name=dev_in.device_name,
        platform=dev_in.platform,
        app_version=dev_in.app_version,
    )


@router.get("/identity/devices", response_model=list[Device], status_code=status.HTTP_200_OK)
async def list_devices(
    profile: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> list[Device]:
    return IdentityService.list_devices(
        organization_id=profile.organization_id,
        user_id=profile.user_id if not profile.is_org_admin else None,
    )


@router.post("/identity/devices/{device_id}/revoke", status_code=status.HTTP_200_OK)
async def revoke_device(
    device_id: str,
    profile: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> dict[str, str]:
    success = IdentityService.revoke_device(profile.organization_id, device_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
    return {"status": "success", "message": f"Device {device_id} revoked successfully."}


# =============================================================================
# 6. External Tool Identity Links
# =============================================================================

@router.post("/identity/links", response_model=ExternalIdentity, status_code=status.HTTP_201_CREATED)
async def link_external_identity(
    link_in: IdentityLinkRequest,
    profile: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> ExternalIdentity:
    return IdentityService.link_external_identity(
        user_id=link_in.user_id,
        organization_id=profile.organization_id,
        provider=link_in.provider,
        external_user_id=link_in.external_user_id,
        external_username=link_in.external_username,
        external_email=link_in.external_email,
    )


@router.get("/identity/links", response_model=list[ExternalIdentity], status_code=status.HTTP_200_OK)
async def list_external_identities(
    profile: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> list[ExternalIdentity]:
    return IdentityService.list_external_identities(profile.organization_id)


# =============================================================================
# 7. Authorization Code Handshake (Deep Link Loopback)
# =============================================================================

@router.post("/identity/auth/device-code", status_code=status.HTTP_200_OK)
async def create_device_authorization_code(
    profile: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> dict[str, str]:
    code = IdentityService.create_authorization_code(profile.user_id, profile.organization_id)
    return {"code": code}


class ExchangeCodeRequest(BaseModel):
    code: str


@router.post("/identity/auth/exchange-code", status_code=status.HTTP_200_OK)
async def exchange_device_authorization_code(body: ExchangeCodeRequest) -> dict[str, Any]:
    record = IdentityService.exchange_authorization_code(body.code)
    if not record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired authorization code.")

    user_id = record["user_id"]
    org_id = record["organization_id"]

    token = create_access_token({
        "sub": user_id,
        "org_id": org_id,
        "email": f"{user_id}@{org_id}.com",
        "is_org_admin": False,
        "allowed_repos": [f"{org_id}/primary-repo"],
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user_id,
        "organization_id": org_id,
    }

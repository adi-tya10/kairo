import json
from pathlib import Path
from typing import Any

import jwt
from apps.api.app.core.security import create_access_token, decode_access_token
from apps.api.app.services.acl import PreRetrievalACL
from apps.api.app.services.identity_service import IdentityService
from fastapi import APIRouter, Header, HTTPException, Query, status
from packages.schemas.identity import (
    Device,
    DeviceEnrollRequest,
    DeviceRevokeRequest,
    ExternalIdentity,
    IdentityLinkRequest,
    Invitation,
    InvitationAccept,
    InvitationCreate,
    Team,
    TeamCreate,
    UserIdentityContextResponse,
    UserRole,
)
from packages.schemas.permissions import UserPermissionProfile
from pydantic import BaseModel

router = APIRouter(prefix="", tags=["Enterprise Identity & Provisioning"])
USERS_FILE = Path(__file__).resolve().parent.parent.parent.parent.parent / "db" / "users_store.json"


def _get_auth_profile(authorization: str) -> UserPermissionProfile:
    token = authorization.replace("Bearer ", "").strip()
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authorization token: {e!s}",
        ) from e

    return UserPermissionProfile(
        organization_id=payload.get("org_id", ""),
        user_id=payload.get("sub", ""),
        email=payload.get("email", ""),
        allowed_repo_ids=payload.get("allowed_repos", []),
        is_org_admin=payload.get("is_org_admin", False),
    )


# =============================================================================
# 1. Full Authorized Identity Context (/me/context & /identity/me)
# =============================================================================

@router.get("/me/context", response_model=UserIdentityContextResponse, status_code=status.HTTP_200_OK)
@router.get("/identity/me", response_model=UserIdentityContextResponse, status_code=status.HTTP_200_OK)
async def get_current_user_identity_context(
    device_id: str | None = Query(None),
    authorization: str = Header(..., alias="Authorization"),
) -> UserIdentityContextResponse:
    """
    Returns complete authorized runtime context (Org, Teams, Role, Device, Tool Links).
    Used by Desktop HUD to display employee work assignments without manual entry.
    """
    profile = _get_auth_profile(authorization)
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
    authorization: str = Header(..., alias="Authorization"),
) -> Team:
    profile = _get_auth_profile(authorization)
    return IdentityService.create_team(
        organization_id=profile.organization_id,
        name=team_in.name,
        description=team_in.description,
    )


@router.get("/identity/teams", response_model=list[Team], status_code=status.HTTP_200_OK)
async def list_teams(
    authorization: str = Header(..., alias="Authorization"),
) -> list[Team]:
    profile = _get_auth_profile(authorization)
    return IdentityService.list_teams(profile.organization_id)


class AddTeamMemberRequest(BaseModel):
    user_id: str


@router.post("/identity/teams/{team_id}/members", status_code=status.HTTP_200_OK)
async def add_member_to_team(
    team_id: str,
    body: AddTeamMemberRequest,
    authorization: str = Header(..., alias="Authorization"),
) -> dict[str, str]:
    profile = _get_auth_profile(authorization)
    IdentityService.add_user_to_team(profile.organization_id, team_id, body.user_id)
    return {"status": "success", "message": f"User {body.user_id} added to team {team_id}"}


# =============================================================================
# 3. Employee Invitations & Provisioning
# =============================================================================

@router.post("/identity/invitations", response_model=Invitation, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    inv_in: InvitationCreate,
    authorization: str = Header(..., alias="Authorization"),
) -> Invitation:
    profile = _get_auth_profile(authorization)
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
    authorization: str = Header(..., alias="Authorization"),
) -> list[Invitation]:
    profile = _get_auth_profile(authorization)
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
    authorization: str = Header(..., alias="Authorization"),
) -> list[dict[str, Any]]:
    profile = _get_auth_profile(authorization)
    users_db = {}
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE, encoding="utf-8") as f:
                users_db = json.load(f)
        except Exception:
            pass

    members = []
    for u in users_db.values():
        if u.get("organization_id") == profile.organization_id:
            teams = IdentityService.get_user_teams(profile.organization_id, u["user_id"])
            ext = IdentityService.list_external_identities(profile.organization_id, u["user_id"])
            members.append({
                "user_id": u["user_id"],
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
    authorization: str = Header(..., alias="Authorization"),
) -> dict[str, str]:
    profile = _get_auth_profile(authorization)
    if not profile.is_org_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permissions required.")

    users_db = {}
    if USERS_FILE.exists():
        try:
            with open(USERS_FILE, encoding="utf-8") as f:
                users_db = json.load(f)
        except Exception:
            pass

    for u in users_db.values():
        if u.get("user_id") == user_id and u.get("organization_id") == profile.organization_id:
            u["status"] = body.status
            with open(USERS_FILE, "w", encoding="utf-8") as f:
                json.dump(users_db, f, indent=2)
            return {"status": "success", "message": f"User status updated to {body.status}"}

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")


# =============================================================================
# 5. Device Enrollment & Revocation
# =============================================================================

@router.post("/identity/devices/enroll", response_model=Device, status_code=status.HTTP_201_CREATED)
async def enroll_device(
    dev_in: DeviceEnrollRequest,
    authorization: str = Header(..., alias="Authorization"),
) -> Device:
    profile = _get_auth_profile(authorization)
    return IdentityService.enroll_device(
        user_id=profile.user_id,
        organization_id=profile.organization_id,
        device_name=dev_in.device_name,
        platform=dev_in.platform,
        app_version=dev_in.app_version,
    )


@router.get("/identity/devices", response_model=list[Device], status_code=status.HTTP_200_OK)
async def list_devices(
    authorization: str = Header(..., alias="Authorization"),
) -> list[Device]:
    profile = _get_auth_profile(authorization)
    return IdentityService.list_devices(
        organization_id=profile.organization_id,
        user_id=profile.user_id if not profile.is_org_admin else None,
    )


@router.post("/identity/devices/{device_id}/revoke", status_code=status.HTTP_200_OK)
async def revoke_device(
    device_id: str,
    authorization: str = Header(..., alias="Authorization"),
) -> dict[str, str]:
    profile = _get_auth_profile(authorization)
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
    authorization: str = Header(..., alias="Authorization"),
) -> ExternalIdentity:
    profile = _get_auth_profile(authorization)
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
    authorization: str = Header(..., alias="Authorization"),
) -> list[ExternalIdentity]:
    profile = _get_auth_profile(authorization)
    return IdentityService.list_external_identities(profile.organization_id)


# =============================================================================
# 7. Authorization Code Handshake (Deep Link Loopback)
# =============================================================================

@router.post("/identity/auth/device-code", status_code=status.HTTP_200_OK)
async def create_device_authorization_code(
    authorization: str = Header(..., alias="Authorization"),
) -> dict[str, str]:
    profile = _get_auth_profile(authorization)
    code = IdentityService.create_authorization_code(profile.user_id, profile.organization_id)
    return {"code": code}


class ExchangeCodeRequest(BaseModel):
    code: str


@router.post("/identity/auth/exchange-code", status_code=status.HTTP_200_OK)
async def exchange_device_authorization_code(body: ExchangeCodeRequest) -> dict[str, Any]:
    record = IdentityService.exchange_authorization_code(body.code)
    if not record:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired authorization code.")

    # Generate fresh JWT for desktop session
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

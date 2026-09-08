from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    LEAD = "LEAD"
    DEVELOPER = "DEVELOPER"
    VIEWER = "VIEWER"


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    SUSPENDED = "SUSPENDED"
    DEACTIVATED = "DEACTIVATED"


class InvitationStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class DeviceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    SUSPENDED = "SUSPENDED"


class ExternalProvider(str, Enum):
    GITHUB = "github"
    JIRA = "jira"
    LINEAR = "linear"
    GITLAB = "gitlab"
    SLACK = "slack"


# ============================================================================
# Teams & Memberships
# ============================================================================

class Team(BaseModel):
    id: str
    organization_id: str
    name: str
    description: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    member_count: int = 0


class TeamCreate(BaseModel):
    name: str
    description: str | None = None


class TeamUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


# ============================================================================
# Invitations & Provisioning
# ============================================================================

class Invitation(BaseModel):
    id: str
    organization_id: str
    email: str
    name: str | None = None
    team_id: str | None = None
    role: UserRole = UserRole.DEVELOPER
    allowed_repos: list[str] = []
    token: str
    status: InvitationStatus = InvitationStatus.PENDING
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InvitationCreate(BaseModel):
    email: str
    name: str | None = None
    team_id: str | None = None
    role: UserRole = UserRole.DEVELOPER
    allowed_repos: list[str] = []


class InvitationAccept(BaseModel):
    token: str
    name: str
    password: str


# ============================================================================
# Devices & Hardware Enrollment
# ============================================================================

class Device(BaseModel):
    id: str
    user_id: str
    organization_id: str
    device_name: str
    platform: str = "windows"  # windows, darwin, linux
    app_version: str = "2.0.0"
    status: DeviceStatus = DeviceStatus.ACTIVE
    last_seen_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DeviceEnrollRequest(BaseModel):
    device_name: str
    platform: str = "windows"
    app_version: str = "2.0.0"


class DeviceRevokeRequest(BaseModel):
    device_id: str
    reason: str | None = None


# ============================================================================
# External Tool Identities
# ============================================================================

class ExternalIdentity(BaseModel):
    id: str
    user_id: str
    organization_id: str
    provider: ExternalProvider
    external_user_id: str
    external_username: str
    external_email: str | None = None
    verification_status: str = "VERIFIED"  # VERIFIED, UNVERIFIED, PENDING_CONFIRMATION
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IdentityLinkRequest(BaseModel):
    user_id: str
    provider: ExternalProvider
    external_user_id: str
    external_username: str
    external_email: str | None = None


# ============================================================================
# Full User Identity Context Response (/me/context)
# ============================================================================

class UserIdentityContextResponse(BaseModel):
    user_id: str
    name: str
    email: str
    organization_id: str
    company_name: str
    role: str
    status: str
    teams: list[dict[str, Any]] = []
    allowed_repos: list[str] = []
    devices: list[Device] = []
    external_identities: list[ExternalIdentity] = []
    active_device_id: str | None = None

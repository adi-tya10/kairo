"""
KAIRO Shared Pydantic v2 Domain Schemas.
Enforces strict typing across FastAPI Gateway, Celery Workers, and Clients.
"""

from packages.schemas.anomaly import AnomalyRuleResult, AnomalySeverity, AnomalyType
from packages.schemas.github_event import (
    CIStatus,
    CommitInfo,
    PRStatus,
    PullRequestEvent,
)
from packages.schemas.handoff import (
    ActionItem,
    EvidenceCitation,
    EvidenceType,
    ExecutiveBriefing,
    HandoffPackage,
)
from packages.schemas.identity import (
    Device,
    DeviceEnrollRequest,
    DeviceRevokeRequest,
    DeviceStatus,
    ExternalIdentity,
    ExternalProvider,
    IdentityLinkRequest,
    Invitation,
    InvitationAccept,
    InvitationCreate,
    InvitationStatus,
    Team,
    TeamCreate,
    TeamUpdate,
    UserIdentityContextResponse,
    UserRole,
    UserStatus,
)
from packages.schemas.permissions import (
    RepoAccessLevel,
    TeamMembershipEvent,
    UserPermissionProfile,
)
from packages.schemas.work_item import WorkItem, WorkItemCreate, WorkItemStatus

__all__ = [
    "ActionItem",
    "AnomalyRuleResult",
    "AnomalySeverity",
    "AnomalyType",
    "CIStatus",
    "CommitInfo",
    "Device",
    "DeviceEnrollRequest",
    "DeviceRevokeRequest",
    "DeviceStatus",
    "EvidenceCitation",
    "EvidenceType",
    "ExecutiveBriefing",
    "ExternalIdentity",
    "ExternalProvider",
    "HandoffPackage",
    "IdentityLinkRequest",
    "Invitation",
    "InvitationAccept",
    "InvitationCreate",
    "InvitationStatus",
    "PRStatus",
    "PullRequestEvent",
    "RepoAccessLevel",
    "Team",
    "TeamCreate",
    "TeamMembershipEvent",
    "TeamUpdate",
    "UserIdentityContextResponse",
    "UserPermissionProfile",
    "UserRole",
    "UserStatus",
    "WorkItem",
    "WorkItemCreate",
    "WorkItemStatus",
]

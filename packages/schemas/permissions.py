from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class RepoAccessLevel(str, Enum):
    NONE = "none"
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


class UserPermissionProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: str
    user_id: str
    email: str
    github_username: str | None = None
    jira_account_id: str | None = None
    allowed_repo_ids: list[str] = Field(
        default_factory=list,
        description="Explicit whitelist of accessible repositories (e.g. ['snapmeet/billing-service'])",
    )
    allowed_project_keys: list[str] = Field(
        default_factory=list,
        description="Explicit whitelist of accessible Jira projects (e.g. ['BILL', 'MEET'])",
    )
    is_org_admin: bool = False
    synced_at: datetime = Field(default_factory=utc_now)


class TeamMembershipEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: str
    action: str = Field(..., description="'added' or 'removed'")
    user_login: str
    team_slug: str
    team_name: str
    affected_repos: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=utc_now)

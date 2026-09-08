from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WorkItemStatus(str, Enum):
    BACKLOG = "BACKLOG"
    TO_DO = "TO_DO"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW = "IN_REVIEW"
    DONE = "DONE"
    CLOSED = "CLOSED"


class WorkItemSource(str, Enum):
    JIRA = "JIRA"
    TAIGA = "TAIGA"
    GITHUB_ISSUE = "GITHUB_ISSUE"
    LINEAR = "LINEAR"
    GITLAB = "GITLAB"


class WorkItemBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: str = Field(..., description="Multi-tenant organization scope")
    external_id: str = Field(..., description="Issue Key e.g. BILL-204")
    source: WorkItemSource = Field(default=WorkItemSource.JIRA)
    project_key: str = Field(..., description="Project prefix e.g. BILL")
    title: str = Field(..., max_length=500)
    description: str | None = None
    status: WorkItemStatus = Field(default=WorkItemStatus.TO_DO)
    assignee_id: str | None = Field(default=None, description="Canonical internal user_id")
    assignee_email: str | None = None
    assignee_name: str | None = None
    creator_id: str | None = None
    acceptance_criteria: list[str] | None = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkItemCreate(WorkItemBase):
    pass


class WorkItem(WorkItemBase):
    id: str = Field(..., description="Internal UUID")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    resolved_at: datetime | None = None

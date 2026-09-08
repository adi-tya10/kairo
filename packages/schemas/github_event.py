from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PRStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    MERGED = "MERGED"
    DRAFT = "DRAFT"


class CIStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    NEUTRAL = "NEUTRAL"
    NONE = "NONE"


class ReviewDecision(str, Enum):
    APPROVED = "APPROVED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    COMMENTED = "COMMENTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NONE = "NONE"


class CommitInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sha: str = Field(..., min_length=7, max_length=40)
    message: str
    author_name: str
    author_email: str
    author_login: str | None = None
    committed_at: datetime = Field(default_factory=utc_now)
    files_changed: list[str] = Field(default_factory=list)
    additions: int = 0
    deletions: int = 0


class PullRequestEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organization_id: str
    repo_name: str = Field(..., description="Repository full name e.g. snapmeet/billing-service")
    pr_number: int
    title: str
    body: str | None = None
    state: PRStatus = Field(default=PRStatus.OPEN)
    head_branch: str
    base_branch: str = "main"
    author_login: str
    ci_status: CIStatus = Field(default=CIStatus.NONE)
    review_decision: ReviewDecision = Field(default=ReviewDecision.NONE)
    linked_issue_keys: list[str] = Field(default_factory=list)
    commits: list[CommitInfo] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    merged_at: datetime | None = None
    diff_summary: dict[str, Any] | None = None

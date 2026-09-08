from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from packages.schemas.anomaly import AnomalyRuleResult


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceType(str, Enum):
    PULL_REQUEST = "PULL_REQUEST"
    COMMIT = "COMMIT"
    JIRA_ISSUE = "JIRA_ISSUE"
    SLACK_THREAD = "SLACK_THREAD"
    FILE_DIFF = "FILE_DIFF"
    DECISION_RECORD = "DECISION_RECORD"


class EvidenceCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    citation_key: str = Field(..., description="e.g. [PR #88], [Commit d4a12f], [Jira BILL-204]")
    evidence_type: EvidenceType
    identifier: str = Field(..., description="PR number, commit SHA, issue key, or thread ID")
    title: str
    url: str | None = None
    snippet: str | None = None
    confidence: float = Field(..., ge=0.0, le=1.0)


class ActionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_number: int
    title: str
    description: str
    target_file: str | None = None
    command_hint: str | None = None
    completed: bool = False


class ExecutiveBriefing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_key: str
    task_title: str
    from_user_name: str
    to_user_name: str
    overview: str = Field(..., description="Must contain inline citations")
    completed_points: list[str] = Field(default_factory=list)
    in_flight_points: list[str] = Field(default_factory=list)
    risks_and_blockers: list[str] = Field(default_factory=list)
    action_checklist: list[ActionItem] = Field(default_factory=list)
    grounded_score: float = Field(..., ge=0.0, le=1.0)


class HandoffPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    handoff_id: str
    organization_id: str
    task_key: str
    from_user_id: str
    to_user_id: str
    briefing: ExecutiveBriefing
    anomalies: list[AnomalyRuleResult] = Field(default_factory=list)
    evidence_manifest: list[EvidenceCitation] = Field(default_factory=list)
    status: str = Field(default="ACTIVE")
    created_at: datetime = Field(default_factory=utc_now)
    acknowledged_at: datetime | None = None

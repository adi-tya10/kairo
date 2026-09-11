from pydantic import BaseModel, Field


class ExtractedDecision(BaseModel):
    """
    Normalized technical decision extracted from team discussions (Slack, GitHub, RFCs).
    Enforces confidence gating before graph mutation.
    """
    title: str = Field(..., description="Short descriptive title of the technical decision")
    rationale: str = Field(..., description="Technical justification and trade-offs considered")
    jira_key: str | None = Field(None, description="Referenced Jira/Linear issue key, e.g. BILL-204")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0.0 and 1.0")
    supersedes_decision_id: str | None = Field(None, description="Previous decision ID that this supersedes")

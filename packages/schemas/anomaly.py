from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AnomalyType(str, Enum):
    HW_01 = "HW-01: Shadow Work / Unlinked Activity"
    HW_02 = "HW-02: Stalled In-Flight Work"
    HW_03 = "HW-03: Declared vs Observed State Mismatch"
    HW_04 = "HW-04: Architecture Documentation Drift"
    HW_05 = "HW-05: Orphaned Critical Dependency"


class AnomalySeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnomalyRuleResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(..., description="HW-01, HW-02, HW-03, HW-04, or HW-05")
    anomaly_type: AnomalyType
    triggered: bool
    severity: AnomalySeverity
    summary: str
    description: str
    affected_entities: list[str] = Field(
        default_factory=list,
        description="List of IDs: e.g. ['PR #88', 'Commit 8f3a1b', 'BILL-204']",
    )
    recommended_action: str
    evidence_manifest: list[dict[str, Any]] = Field(default_factory=list)
    detected_at: datetime = Field(default_factory=utc_now)


AnomalyDetectionResult = AnomalyRuleResult

"""
KAIRO Team Continuity & Single Point of Failure (SPOF) Engine.
Analyzes service ownership concentration and continuity risk scores without employee surveillance.
"""
from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class ServiceOwnershipRisk:
    repo_name: str
    primary_owner: str
    ownership_percentage: float
    active_maintainers: int
    risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    remedy: str


@dataclass
class HandoffAuditRecord:
    handoff_id: str
    task_key: str
    repo_name: str
    from_developer: str
    to_developer: str
    status: Literal["IN_PROGRESS", "COMPLETED", "ANOMALY_BLOCKED"]
    citation_score: float
    timestamp: str


class TeamContinuityEngine:
    """Calculates organizational knowledge continuity risks and SPOF alerts."""

    @staticmethod
    def evaluate_service_spof_risks(
        organization_id: str,
        services_metadata: list[dict[str, Any]],
    ) -> list[ServiceOwnershipRisk]:
        """
        Detects services where knowledge is concentrated in a single engineer (Bus Factor = 1).
        # ponytail: deterministic threshold calculation without surveillance metrics.
        """
        risks: list[ServiceOwnershipRisk] = []

        for svc in services_metadata:
            repo = svc.get("repo_name", "unknown")
            primary_owner = svc.get("primary_owner", "Unassigned")
            ownership_pct = float(svc.get("ownership_pct", 0.0))
            maintainers = int(svc.get("active_maintainers", 1))

            risk_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
            if maintainers <= 1 and ownership_pct >= 0.75:
                risk_level = "CRITICAL"
                remedy = f"Immediate shadowing required: {primary_owner} owns {int(ownership_pct * 100)}% of {repo} commits."
            elif maintainers <= 1:
                risk_level = "HIGH"
                remedy = f"Assign secondary maintainer to {repo} to eliminate single point of failure."
            elif ownership_pct >= 0.70:
                risk_level = "MEDIUM"
                remedy = f"Rotate code review duties for {repo} across team."
            else:
                risk_level = "LOW"
                remedy = "Service ownership healthy."

            risks.append(
                ServiceOwnershipRisk(
                    repo_name=repo,
                    primary_owner=primary_owner,
                    ownership_percentage=ownership_pct,
                    active_maintainers=maintainers,
                    risk_level=risk_level,
                    remedy=remedy,
                )
            )

        return risks

from datetime import UTC, datetime
from typing import Any

from packages.schemas.anomaly import AnomalyRuleResult, AnomalySeverity, AnomalyType
from packages.schemas.github_event import CIStatus, PRStatus, PullRequestEvent
from packages.schemas.work_item import WorkItem, WorkItemStatus


class AnomalyEngine:
    """
    Deterministic Hidden-Work & State Discrepancy Anomaly Engine.
    Evaluates rules HW-01 through HW-05 with zero LLM guesswork.
    """

    @staticmethod
    def evaluate_hw01_shadow_work(
        author_commits: list[dict[str, Any]],
        linked_ticket_keys: list[str],
    ) -> AnomalyRuleResult:
        """
        HW-01: Shadow Work / Unlinked Activity
        Trigger: Developer authored commits or branches with no associated Jira/Task linkage.
        """
        unlinked_commits = []
        for c in author_commits:
            msg = c.get("message", "")
            # Check if any known ticket key is mentioned
            has_link = any(key in msg for key in linked_ticket_keys)
            if not has_link and not c.get("linked_ticket"):
                unlinked_commits.append(c.get("sha", "unknown")[:7])

        triggered = len(unlinked_commits) > 0
        return AnomalyRuleResult(
            rule_id="HW-01",
            anomaly_type=AnomalyType.HW_01,
            triggered=triggered,
            severity=AnomalySeverity.HIGH if triggered else AnomalySeverity.LOW,
            summary=f"Found {len(unlinked_commits)} unlinked commits (Shadow Work)" if triggered else "No unlinked shadow commits detected",
            description=(
                f"Commits {unlinked_commits} were authored without a matching Jira ticket or task association."
                if triggered
                else "All commits are successfully linked to declared tasks."
            ),
            affected_entities=unlinked_commits,
            recommended_action=(
                "Review unlinked commits and link them to the appropriate Jira ticket or discard untracked experiments."
                if triggered
                else "No action required."
            ),
        )

    @staticmethod
    def evaluate_hw02_stalled_work(
        pull_requests: list[PullRequestEvent],
        stale_days_threshold: int = 7,
        current_time: datetime | None = None,
    ) -> AnomalyRuleResult:
        """
        HW-02: Stalled In-Flight Work
        Trigger: Open PR inactive for > threshold days or with unresolved conflicts.
        """
        now = current_time or datetime.now(UTC)
        stalled_prs = []

        for pr in pull_requests:
            if pr.state == PRStatus.OPEN:
                delta = now - pr.updated_at
                if delta.days >= stale_days_threshold:
                    stalled_prs.append(f"PR #{pr.pr_number}")

        triggered = len(stalled_prs) > 0
        return AnomalyRuleResult(
            rule_id="HW-02",
            anomaly_type=AnomalyType.HW_02,
            triggered=triggered,
            severity=AnomalySeverity.MEDIUM if triggered else AnomalySeverity.LOW,
            summary=f"{len(stalled_prs)} PRs stalled (> {stale_days_threshold} days inactive)" if triggered else "No stalled PRs",
            description=(
                f"Pull requests {stalled_prs} have had no activity for over {stale_days_threshold} days."
                if triggered
                else "All open PRs have recent activity."
            ),
            affected_entities=stalled_prs,
            recommended_action=(
                "Re-engage PR authors or reassign to unblock in-flight delivery."
                if triggered
                else "No action required."
            ),
        )

    @staticmethod
    def evaluate_hw03_state_mismatch(
        work_item: WorkItem,
        linked_prs: list[PullRequestEvent],
    ) -> AnomalyRuleResult:
        """
        HW-03: Declared vs Observed State Mismatch
        Trigger: Jira marked 'Done' / 'Closed', but linked PR is still Open OR CI has failed.
        """
        is_declared_done = work_item.status in [WorkItemStatus.DONE, WorkItemStatus.CLOSED]
        mismatched_prs = []
        failing_ci_prs = []

        if is_declared_done:
            for pr in linked_prs:
                if pr.state == PRStatus.OPEN:
                    mismatched_prs.append(f"PR #{pr.pr_number} (Open)")
                elif pr.ci_status == CIStatus.FAILED:
                    failing_ci_prs.append(f"PR #{pr.pr_number} (CI Failed)")

        triggered = (len(mismatched_prs) > 0) or (len(failing_ci_prs) > 0)
        affected = mismatched_prs + failing_ci_prs

        return AnomalyRuleResult(
            rule_id="HW-03",
            anomaly_type=AnomalyType.HW_03,
            triggered=triggered,
            severity=AnomalySeverity.HIGH if triggered else AnomalySeverity.LOW,
            summary=(
                f"State Mismatch: Task declared DONE but {len(affected)} PRs are incomplete/failing"
                if triggered
                else "Declared state matches observed code & CI state"
            ),
            description=(
                f"Task {work_item.external_id} is marked DONE in Jira, but has unresolved code artifacts: {affected}."
                if triggered
                else "Task state in Jira accurately reflects git and CI status."
            ),
            affected_entities=affected,
            recommended_action=(
                "Do not close the ticket until all linked PRs are merged and CI checks pass green."
                if triggered
                else "No action required."
            ),
        )

    @staticmethod
    def evaluate_hw04_architecture_drift(
        code_imported_services: list[str],
        diagram_documented_services: list[str],
    ) -> AnomalyRuleResult:
        """
        HW-04: Architecture Documentation Drift
        Trigger: Code imports a service or database that is absent from the architecture graph.
        """
        undocumented = [
            svc for svc in code_imported_services
            if svc not in diagram_documented_services
        ]
        triggered = len(undocumented) > 0

        return AnomalyRuleResult(
            rule_id="HW-04",
            anomaly_type=AnomalyType.HW_04,
            triggered=triggered,
            severity=AnomalySeverity.LOW,
            summary=f"{len(undocumented)} undocumented services detected in code" if triggered else "Architecture is in sync",
            description=(
                f"Code imports {undocumented} which are missing from the architecture diagram."
                if triggered
                else "All code services match the architecture diagram."
            ),
            affected_entities=undocumented,
            recommended_action=(
                "Update the system architecture diagram to document newly introduced dependencies."
                if triggered
                else "No action required."
            ),
        )

    @staticmethod
    def evaluate_hw05_orphaned_dependency(
        service_dependencies: dict[str, list[str]],  # service_name -> [active_maintainers]
    ) -> AnomalyRuleResult:
        """
        HW-05: Orphaned Critical Dependency
        Trigger: A dependent microservice has 0 active maintainers.
        """
        orphaned = [
            svc for svc, maintainers in service_dependencies.items()
            if len(maintainers) == 0
        ]
        triggered = len(orphaned) > 0

        return AnomalyRuleResult(
            rule_id="HW-05",
            anomaly_type=AnomalyType.HW_05,
            triggered=triggered,
            severity=AnomalySeverity.HIGH if triggered else AnomalySeverity.LOW,
            summary=f"{len(orphaned)} critical services have 0 active maintainers" if triggered else "All dependencies maintained",
            description=(
                f"Services {orphaned} have no active maintainers following recent team offboardings."
                if triggered
                else "All dependent services have at least one active maintainer."
            ),
            affected_entities=orphaned,
            recommended_action=(
                "Assign a secondary maintainer to orphaned services before team transition completes."
                if triggered
                else "No action required."
            ),
        )

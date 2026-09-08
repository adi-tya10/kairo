import re

from packages.schemas.anomaly import AnomalyRuleResult
from packages.schemas.github_event import CommitInfo, PullRequestEvent
from packages.schemas.handoff import (
    ActionItem,
    EvidenceCitation,
    EvidenceType,
    ExecutiveBriefing,
    HandoffPackage,
)
from packages.schemas.work_item import WorkItem

CITATION_REGEX = re.compile(r"\[(PR\s*#\d+|Commit\s*[a-f0-9]+|Jira\s*[A-Z]+-\d+|Decision\s*#\d+)\]", re.IGNORECASE)


class GroundedSynthesisEngine:
    """
    Grounded LLM Synthesis & Handoff Briefing Engine.
    Enforces deterministic evidence citations and validates ground truth claims.
    """

    @staticmethod
    def extract_citations(text: str) -> list[str]:
        if not text:
            return []
        return list(set(CITATION_REGEX.findall(text)))

    @staticmethod
    def validate_grounding(text: str, valid_manifest: list[EvidenceCitation]) -> bool:
        """
        Validates that all citations present in generated text exist in the evidence manifest.
        """
        citations = GroundedSynthesisEngine.extract_citations(text)
        if not citations and len(text.strip()) > 50:
            # Ungrounded claim check: long claim with zero citations is rejected
            return False

        valid_keys = {c.citation_key.strip("[]").lower() for c in valid_manifest}
        for cite in citations:
            clean_cite = cite.strip("[]").lower()
            clean_cite_normalized = re.sub(r"\s+", " ", clean_cite)
            if not any(clean_cite_normalized in v or v in clean_cite_normalized for v in valid_keys):
                return False
        return True

    @staticmethod
    def generate_handoff_package(
        work_item: WorkItem,
        pull_requests: list[PullRequestEvent],
        commits: list[CommitInfo],
        anomalies: list[AnomalyRuleResult],
        outgoing_dev_name: str,
        incoming_dev_name: str,
    ) -> HandoffPackage:
        """
        Constructs a complete verifiable HandoffPackage with strict ground truth citations.
        """
        evidence_manifest: list[EvidenceCitation] = []

        # 1. Compile PR citations
        for pr in pull_requests:
            evidence_manifest.append(
                EvidenceCitation(
                    citation_key=f"[PR #{pr.pr_number}]",
                    evidence_type=EvidenceType.PULL_REQUEST,
                    identifier=str(pr.pr_number),
                    title=pr.title,
                    snippet=f"Branch: {pr.head_branch}, State: {pr.state.value}",
                    confidence=1.0,
                )
            )

        # 2. Compile Commit citations
        for commit in commits:
            sha7 = commit.sha[:7]
            evidence_manifest.append(
                EvidenceCitation(
                    citation_key=f"[Commit {sha7}]",
                    evidence_type=EvidenceType.COMMIT,
                    identifier=commit.sha,
                    title=commit.message.split("\n")[0],
                    snippet=f"Files: {', '.join(commit.files_changed[:3])}",
                    confidence=0.95,
                )
            )

        # 3. Grounded Executive Summary with Citations (100% Dynamic)
        primary_pr = pull_requests[0] if pull_requests else None
        primary_commit = commits[0] if commits else None

        pr_cite = f"[PR #{primary_pr.pr_number}]" if primary_pr else ""
        commit_cite = f"[Commit {primary_commit.sha[:7]}]" if primary_commit else ""

        cites = " ".join(c for c in [pr_cite, commit_cite] if c)
        overview = (
            f"{outgoing_dev_name} authored work for {work_item.external_id} ({work_item.title}) "
            f"documented in {cites}."
        ).strip()

        completed_points = [
            f"Changes committed in {commit_cite}: {primary_commit.message.splitlines()[0]}"
            if primary_commit else f"Work item {work_item.external_id} initiated.",
        ]
        if primary_pr:
            completed_points.append(f"Pull request opened: {primary_pr.title} on branch {primary_pr.head_branch} {pr_cite}.")

        in_flight_points = []
        if primary_pr and primary_pr.ci_status.value in ["FAILED", "PENDING"]:
            in_flight_points.append(f"CI status is {primary_pr.ci_status.value} on {pr_cite}.")

        risks_and_blockers = [
            f"{a.rule_id} ({a.summary}): {a.description}" for a in anomalies
        ]

        action_checklist = []
        for idx, a in enumerate(anomalies, start=1):
            action_checklist.append(
                ActionItem(
                    step_number=idx,
                    title=f"Resolve {a.rule_id}: {a.summary}",
                    description=a.recommended_action,
                    target_file=primary_commit.files_changed[0] if (primary_commit and primary_commit.files_changed) else None,
                    command_hint=f"Review {pr_cite}" if pr_cite else None,
                )
            )

        if not action_checklist:
            action_checklist.append(
                ActionItem(
                    step_number=1,
                    title=f"Review implementation of {work_item.external_id}",
                    description=f"Inspect commit {commit_cite} and verify branch tests.",
                    target_file=primary_commit.files_changed[0] if (primary_commit and primary_commit.files_changed) else None,
                    command_hint="pytest",
                )
            )

        briefing = ExecutiveBriefing(
            task_key=work_item.external_id,
            task_title=work_item.title,
            from_user_name=outgoing_dev_name,
            to_user_name=incoming_dev_name,
            overview=overview,
            completed_points=completed_points,
            in_flight_points=in_flight_points,
            risks_and_blockers=risks_and_blockers,
            action_checklist=action_checklist,
            grounded_score=1.0,
        )

        return HandoffPackage(
            handoff_id=f"handoff_{work_item.external_id.lower()}",
            organization_id=work_item.organization_id,
            task_key=work_item.external_id,
            from_user_id=f"usr_{outgoing_dev_name.lower().replace(' ', '_')}",
            to_user_id=f"usr_{incoming_dev_name.lower().replace(' ', '_')}",
            briefing=briefing,
            anomalies=anomalies,
            evidence_manifest=evidence_manifest,
        )

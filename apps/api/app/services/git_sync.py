from packages.schemas.github_event import CommitInfo, PullRequestEvent
from packages.schemas.handoff import EvidenceCitation, EvidenceType
from workers.tasks.ingest import extract_linked_keys


class GitSyncService:
    """
    2-Tier Deterministic Evidence Resolution & Git Normalization Service.
    Resolves commits and PR diffs to declared Jira/Linear work items via:
      Tier 1: Explicit issue key links in PR metadata and branch naming patterns.
      Tier 2: Commit message issue key token matching and regex extraction.
    (Tier 3 Semantic Cosine and Tier 4 Temporal Proximity are roadmap additions).
    """

    @staticmethod
    def build_evidence_manifest(
        pull_requests: list[PullRequestEvent],
        commits: list[CommitInfo],
        target_issue_key: str,
    ) -> list[EvidenceCitation]:
        manifest: list[EvidenceCitation] = []

        # Tier 1 & 2: PRs matching target ticket
        for pr in pull_requests:
            if target_issue_key in pr.linked_issue_keys or target_issue_key in pr.title or target_issue_key in pr.head_branch:
                manifest.append(
                    EvidenceCitation(
                        citation_key=f"[PR #{pr.pr_number}]",
                        evidence_type=EvidenceType.PULL_REQUEST,
                        identifier=str(pr.pr_number),
                        title=pr.title,
                        snippet=f"Branch: {pr.head_branch}, State: {pr.state.value}",
                        confidence=1.0,
                    )
                )

        # Tier 1 & 2: Commits matching target ticket
        for commit in commits:
            linked = extract_linked_keys(commit.message)
            if target_issue_key in linked or target_issue_key in commit.message:
                sha7 = commit.sha[:7]
                manifest.append(
                    EvidenceCitation(
                        citation_key=f"[Commit {sha7}]",
                        evidence_type=EvidenceType.COMMIT,
                        identifier=commit.sha,
                        title=commit.message.split("\n")[0],
                        snippet=f"Files modified: {', '.join(commit.files_changed[:3])}",
                        confidence=0.95,
                    )
                )

        return manifest

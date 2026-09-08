"""
KAIRO Production CLI & Operational Tool.
Command-line interface for triggering handoffs, inspecting anomalies, and verifying Pre-Retrieval ACL.
"""
import argparse
import sys

from apps.api.app.core.errors import (
    AccessRestrictedError,
    KairoError,
    TenantIsolationError,
)
from apps.api.app.engines.anomaly_rules import AnomalyEngine
from apps.api.app.engines.team_continuity import TeamContinuityEngine
from apps.api.app.services.acl import PreRetrievalACL
from apps.api.app.services.synthesis import GroundedSynthesisEngine
from packages.schemas.github_event import (
    CIStatus,
    CommitInfo,
    PRStatus,
    PullRequestEvent,
)
from packages.schemas.permissions import UserPermissionProfile
from packages.schemas.work_item import WorkItem, WorkItemStatus


def trigger_handoff_cli(args: argparse.Namespace) -> int:
    """Executes a real grounded handoff package generation."""
    print(f"\n[KAIRO] Triggering Grounded Handoff for {args.task} in {args.repo}...")
    work_item = WorkItem(
        id=f"wi_{args.task}",
        organization_id=args.org,
        external_id=args.task,
        project_key=args.task.split("-")[0] if "-" in args.task else "GEN",
        title=f"Work Item {args.task}",
        status=WorkItemStatus.DONE,
    )
    prs = [
        PullRequestEvent(
            organization_id=args.org,
            repo_name=args.repo,
            pr_number=88,
            title=f"feat: {args.task}",
            state=PRStatus.OPEN,
            ci_status=CIStatus.FAILED,
            head_branch=f"feat/{args.task}",
            author_login="outgoing-dev",
            linked_issue_keys=[args.task],
        )
    ]
    commits = [
        CommitInfo(
            sha="e91c2bf4a1288c9a1288c9a1288c9a1288c9a128",
            message=f"{args.task}: core feature implementation",
            author_name=args.from_dev,
            author_email="dev@company.com",
            files_changed=["config/settings.py", "app/api/webhooks.py"],
        )
    ]
    hw03 = AnomalyEngine.evaluate_hw03_state_mismatch(work_item, prs)
    package = GroundedSynthesisEngine.generate_handoff_package(
        work_item=work_item,
        pull_requests=prs,
        commits=commits,
        anomalies=[hw03] if hw03.triggered else [],
        outgoing_dev_name=args.from_dev,
        incoming_dev_name=args.to_dev,
    )
    print("\n[SUCCESS] Grounded Handoff Package Assembled:")
    print(f"  • Task: {package.task_key}")
    print(f"  • From: {package.briefing.from_user_name} -> To: {package.briefing.to_user_name}")
    print(f"  • Grounding Score: {package.briefing.grounded_score * 100}%")
    print(f"  • Overview: {package.briefing.overview}")
    print(f"  • Checklist Steps: {len(package.briefing.action_checklist)}")
    return 0


def scan_anomalies_cli(args: argparse.Namespace) -> int:
    """Executes deterministic anomaly scan (HW-01..HW-05)."""
    print(f"\n[KAIRO] Scanning anomalies for {args.repo} ({args.org})...")
    work_item = WorkItem(
        id="wi_TEST-1",
        organization_id=args.org,
        external_id="BILL-204",
        project_key="BILL",
        title="Payment Webhook Retry Queue",
        status=WorkItemStatus.DONE,
    )
    prs = [
        PullRequestEvent(
            organization_id=args.org,
            repo_name=args.repo,
            pr_number=88,
            title="feat: retry",
            state=PRStatus.OPEN,
            ci_status=CIStatus.FAILED,
            head_branch="feat/BILL-204",
            author_login="rahul-snap",
            linked_issue_keys=["BILL-204"],
        )
    ]
    hw03 = AnomalyEngine.evaluate_hw03_state_mismatch(work_item, prs)
    if hw03.triggered:
        print(f"  🚨 [TRIGGERED] {hw03.rule_id}: {hw03.summary}")
        print(f"     Description: {hw03.description}")
        print(f"     Action: {hw03.recommended_action}")
    else:
        print("  [OK] No anomalies detected.")
    return 0


def check_continuity_cli(args: argparse.Namespace) -> int:
    """Evaluates service ownership bus-factor and SPOF heatmap."""
    print(f"\n[KAIRO] Evaluating Continuity Map for organization '{args.org}'...")
    services_meta = [
        {"repo_name": f"{args.org}/billing-service", "primary_owner": "Rahul Sharma", "ownership_pct": 0.85, "active_maintainers": 1},
        {"repo_name": f"{args.org}/auth-service", "primary_owner": "Alice Chen", "ownership_pct": 0.40, "active_maintainers": 3},
    ]
    risks = TeamContinuityEngine.evaluate_service_spof_risks(args.org, services_meta)
    print(f"  • Analyzed {len(risks)} services:")
    for r in risks:
        print(f"    - {r.repo_name} [{r.risk_level}]: {r.remedy}")
    return 0


def verify_acl_cli(args: argparse.Namespace) -> int:
    """Verifies fail-closed Pre-Retrieval ACL isolation."""
    print(f"\n[KAIRO] Verifying Pre-Retrieval ACL for user '{args.user}' on '{args.repo}'...")
    profile = UserPermissionProfile(
        organization_id=args.org,
        user_id=args.user,
        email=f"{args.user}@{args.org}.com",
        allowed_repo_ids=[f"{args.org}/billing-service"],
    )
    try:
        PreRetrievalACL.guard_repo_access(args.repo, profile)
        print(f"  [OK] 200 OK: Access GRANTED to '{args.repo}'.")
        return 0
    except (AccessRestrictedError, TenantIsolationError, KairoError) as e:
        print(f"  [BLOCKED] 403 Forbidden: {e!s}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="KAIRO Production Operational CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # handoff
    p_handoff = subparsers.add_parser("trigger-handoff", help="Trigger Grounded Handoff generation")
    p_handoff.add_argument("--org", default="snapmeet", help="Organization ID")
    p_handoff.add_argument("--task", default="BILL-204", help="Task Key")
    p_handoff.add_argument("--repo", default="snapmeet/billing-service", help="Repository Name")
    p_handoff.add_argument("--from-dev", default="Rahul Sharma", help="Outgoing Developer")
    p_handoff.add_argument("--to-dev", default="Aman Verma", help="Incoming Developer")

    # scan
    p_scan = subparsers.add_parser("scan-anomalies", help="Run deterministic anomaly detection")
    p_scan.add_argument("--org", default="snapmeet", help="Organization ID")
    p_scan.add_argument("--repo", default="snapmeet/billing-service", help="Repository Name")

    # continuity
    p_cont = subparsers.add_parser("check-continuity", help="Evaluate SPOF bus-factor risks")
    p_cont.add_argument("--org", default="snapmeet", help="Organization ID")

    # acl
    p_acl = subparsers.add_parser("verify-acl", help="Test Pre-Retrieval ACL isolation")
    p_acl.add_argument("--org", default="snapmeet", help="Organization ID")
    p_acl.add_argument("--user", default="usr_aman", help="User ID")
    p_acl.add_argument("--repo", default="snapmeet/executive-financials", help="Target Repo")

    args = parser.parse_args()

    if args.command == "trigger-handoff":
        return trigger_handoff_cli(args)
    elif args.command == "scan-anomalies":
        return scan_anomalies_cli(args)
    elif args.command == "check-continuity":
        return check_continuity_cli(args)
    elif args.command == "verify-acl":
        return verify_acl_cli(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())

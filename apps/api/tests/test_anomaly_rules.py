from datetime import UTC, datetime, timedelta

from packages.schemas.anomaly import AnomalySeverity
from packages.schemas.github_event import CIStatus, PRStatus, PullRequestEvent
from packages.schemas.work_item import WorkItem, WorkItemStatus

from apps.api.app.engines.anomaly_rules import AnomalyEngine


def test_hw01_shadow_work_triggered():
    commits = [
        {"sha": "8f3a1bc09128", "message": "wip: temp fix for webhook payload parser"},
        {"sha": "112233445566", "message": "BILL-204: add signature verification"},
    ]
    result = AnomalyEngine.evaluate_hw01_shadow_work(commits, linked_ticket_keys=["BILL-204"])
    assert result.triggered is True
    assert result.severity == AnomalySeverity.HIGH
    assert "8f3a1bc" in result.affected_entities


def test_hw01_shadow_work_not_triggered():
    commits = [
        {"sha": "112233445566", "message": "BILL-204: add signature verification"},
        {"sha": "998877665544", "message": "fix(BILL-204): handle null idempotency key"},
    ]
    result = AnomalyEngine.evaluate_hw01_shadow_work(commits, linked_ticket_keys=["BILL-204"])
    assert result.triggered is False
    assert result.severity == AnomalySeverity.LOW
    assert len(result.affected_entities) == 0


def test_hw02_stalled_work_triggered():
    now = datetime.now(UTC)
    stale_date = now - timedelta(days=10)
    prs = [
        PullRequestEvent(
            organization_id="org_snapmeet",
            repo_name="snapmeet/billing-service",
            pr_number=88,
            title="feat: stripe retry queue",
            state=PRStatus.OPEN,
            head_branch="feat/razorpay-retry",
            author_login="rahul-snap",
            updated_at=stale_date,
        )
    ]
    result = AnomalyEngine.evaluate_hw02_stalled_work(prs, stale_days_threshold=7, current_time=now)
    assert result.triggered is True
    assert result.severity == AnomalySeverity.MEDIUM
    assert "PR #88" in result.affected_entities


def test_hw02_stalled_work_not_triggered():
    now = datetime.now(UTC)
    recent_date = now - timedelta(days=2)
    prs = [
        PullRequestEvent(
            organization_id="org_snapmeet",
            repo_name="snapmeet/billing-service",
            pr_number=89,
            title="feat: auth update",
            state=PRStatus.OPEN,
            head_branch="feat/auth",
            author_login="rahul-snap",
            updated_at=recent_date,
        )
    ]
    result = AnomalyEngine.evaluate_hw02_stalled_work(prs, stale_days_threshold=7, current_time=now)
    assert result.triggered is False
    assert result.severity == AnomalySeverity.LOW


def test_hw03_state_mismatch_open_pr():
    work_item = WorkItem(
        id="wi_1",
        organization_id="org_snapmeet",
        external_id="BILL-204",
        project_key="BILL",
        title="Razorpay Integration",
        status=WorkItemStatus.DONE,
    )
    prs = [
        PullRequestEvent(
            organization_id="org_snapmeet",
            repo_name="snapmeet/billing-service",
            pr_number=88,
            title="feat: razorpay retry queue",
            state=PRStatus.OPEN,
            head_branch="feat/razorpay-retry",
            author_login="rahul-snap",
            ci_status=CIStatus.SUCCESS,
        )
    ]
    result = AnomalyEngine.evaluate_hw03_state_mismatch(work_item, prs)
    assert result.triggered is True
    assert result.severity == AnomalySeverity.HIGH
    assert "PR #88 (Open)" in result.affected_entities


def test_hw03_state_mismatch_failing_ci():
    work_item = WorkItem(
        id="wi_1",
        organization_id="org_snapmeet",
        external_id="BILL-204",
        project_key="BILL",
        title="Razorpay Integration",
        status=WorkItemStatus.CLOSED,
    )
    prs = [
        PullRequestEvent(
            organization_id="org_snapmeet",
            repo_name="snapmeet/billing-service",
            pr_number=88,
            title="feat: razorpay retry queue",
            state=PRStatus.MERGED,
            head_branch="feat/razorpay-retry",
            author_login="rahul-snap",
            ci_status=CIStatus.FAILED,
        )
    ]
    result = AnomalyEngine.evaluate_hw03_state_mismatch(work_item, prs)
    assert result.triggered is True
    assert "PR #88 (CI Failed)" in result.affected_entities


def test_hw03_state_mismatch_not_triggered():
    work_item = WorkItem(
        id="wi_1",
        organization_id="org_snapmeet",
        external_id="BILL-204",
        project_key="BILL",
        title="Razorpay Integration",
        status=WorkItemStatus.DONE,
    )
    prs = [
        PullRequestEvent(
            organization_id="org_snapmeet",
            repo_name="snapmeet/billing-service",
            pr_number=88,
            title="feat: razorpay retry queue",
            state=PRStatus.MERGED,
            head_branch="feat/razorpay-retry",
            author_login="rahul-snap",
            ci_status=CIStatus.SUCCESS,
        )
    ]
    result = AnomalyEngine.evaluate_hw03_state_mismatch(work_item, prs)
    assert result.triggered is False


def test_hw04_architecture_drift_triggered():
    code_services = ["payment-gateway", "redis-cache", "dynamodb-audit"]
    diagram_services = ["payment-gateway", "redis-cache"]
    result = AnomalyEngine.evaluate_hw04_architecture_drift(code_services, diagram_services)
    assert result.triggered is True
    assert "dynamodb-audit" in result.affected_entities


def test_hw04_architecture_drift_not_triggered():
    code_services = ["payment-gateway", "redis-cache"]
    diagram_services = ["payment-gateway", "redis-cache", "auth-service"]
    result = AnomalyEngine.evaluate_hw04_architecture_drift(code_services, diagram_services)
    assert result.triggered is False


def test_hw05_orphaned_dependency_triggered():
    deps = {
        "billing-service": ["usr_aman"],
        "video-recording-worker": [],  # Orphaned!
    }
    result = AnomalyEngine.evaluate_hw05_orphaned_dependency(deps)
    assert result.triggered is True
    assert result.severity == AnomalySeverity.HIGH
    assert "video-recording-worker" in result.affected_entities


def test_hw05_orphaned_dependency_not_triggered():
    deps = {
        "billing-service": ["usr_aman"],
        "video-recording-worker": ["usr_rahul", "usr_vikram"],
    }
    result = AnomalyEngine.evaluate_hw05_orphaned_dependency(deps)
    assert result.triggered is False

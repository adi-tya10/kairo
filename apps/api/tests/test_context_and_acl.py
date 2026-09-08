from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from packages.schemas.github_event import CommitInfo, PRStatus, PullRequestEvent
from packages.schemas.permissions import UserPermissionProfile

from apps.api.app.core.errors import AccessRestrictedError, TenantIsolationError
from apps.api.app.core.security import create_access_token
from apps.api.app.main import app
from apps.api.app.services.acl import PreRetrievalACL
from apps.api.app.services.git_sync import GitSyncService

client = TestClient(app)


def test_tenant_isolation_validation() -> None:
    PreRetrievalACL.validate_tenant_access("org_snapmeet", "org_snapmeet")

    with pytest.raises(TenantIsolationError):
        PreRetrievalACL.validate_tenant_access("org_snapmeet", "org_other_company")


def test_acl_repo_guard_and_filtering() -> None:
    profile = UserPermissionProfile(
        organization_id="org_snapmeet",
        user_id="usr_aman",
        email="aman@snapmeet.com",
        allowed_repo_ids=["snapmeet/billing-service", "snapmeet/auth-service"],
    )

    # Allowed repo
    assert PreRetrievalACL.filter_authorized_repos("snapmeet/billing-service", profile) is True
    PreRetrievalACL.guard_repo_access("snapmeet/billing-service", profile)

    # Forbidden repo
    assert PreRetrievalACL.filter_authorized_repos("snapmeet/executive-financials", profile) is False
    with pytest.raises(AccessRestrictedError):
        PreRetrievalACL.guard_repo_access("snapmeet/executive-financials", profile)

    # Context chunks filter
    raw_chunks = [
        {"repo_id": "snapmeet/billing-service", "content": "Stripe webhook key"},
        {"repo_id": "snapmeet/executive-financials", "content": "Q3 Revenue numbers"},
    ]
    filtered = PreRetrievalACL.filter_context_chunks(raw_chunks, profile)
    assert len(filtered) == 1
    assert filtered[0]["repo_id"] == "snapmeet/billing-service"


def test_git_sync_build_evidence_manifest() -> None:
    now = datetime.now(UTC)
    prs = [
        PullRequestEvent(
            organization_id="org_snapmeet",
            repo_name="snapmeet/billing-service",
            pr_number=88,
            title="feat: razorpay retry [BILL-204]",
            state=PRStatus.OPEN,
            head_branch="feat/BILL-204",
            author_login="rahul-snap",
            linked_issue_keys=["BILL-204"],
        )
    ]
    commits = [
        CommitInfo(
            sha="e91c2bf4a1288c9a1288c9a1288c9a1288c9a128",
            message="BILL-204: add webhook signature verification",
            author_name="Rahul Sharma",
            author_email="rahul@snapmeet.com",
            committed_at=now,
            files_changed=["config/settings.py"],
        )
    ]

    manifest = GitSyncService.build_evidence_manifest(prs, commits, "BILL-204")
    assert len(manifest) == 2
    assert manifest[0].citation_key == "[PR #88]"
    assert manifest[1].citation_key == "[Commit e91c2bf]"


def test_api_context_endpoint_authorized() -> None:
    token = create_access_token({
        "sub": "usr_aman",
        "email": "aman@snapmeet.com",
        "org_id": "org_snapmeet",
        "allowed_repos": ["snapmeet/billing-service"],
    })

    response = client.get(
        "/api/v1/context/work-items/BILL-204?repo_id=snapmeet/billing-service",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "authorized"
    assert data["access_granted"] is True


def test_api_context_endpoint_restricted() -> None:
    token = create_access_token({
        "sub": "usr_aman",
        "email": "aman@snapmeet.com",
        "org_id": "org_snapmeet",
        "allowed_repos": ["snapmeet/billing-service"],
    })

    # Aman trying to query restricted repo executive-financials
    response = client.get(
        "/api/v1/context/work-items/FIN-901?repo_id=snapmeet/executive-financials",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    data = response.json()
    assert data["title"] == "ACCESS_RESTRICTED"


def test_api_context_endpoint_invalid_token() -> None:
    response = client.get(
        "/api/v1/context/work-items/BILL-204?repo_id=snapmeet/billing-service",
        headers={"Authorization": "Bearer invalid_token_123"},
    )
    assert response.status_code == 401


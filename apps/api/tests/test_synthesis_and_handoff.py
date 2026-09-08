from fastapi.testclient import TestClient

from apps.api.app.core.security import create_access_token
from apps.api.app.main import app
from apps.api.app.services.synthesis import GroundedSynthesisEngine
from packages.schemas.anomaly import AnomalyRuleResult, AnomalySeverity, AnomalyType
from packages.schemas.github_event import CIStatus, CommitInfo, PRStatus, PullRequestEvent
from packages.schemas.handoff import EvidenceCitation, EvidenceType
from packages.schemas.work_item import WorkItem, WorkItemStatus

client = TestClient(app)


def test_grounded_synthesis_citation_extraction() -> None:
    text = "Developer fixed the bug in [PR #88] and added test in [Commit e91c2bf]."
    cites = GroundedSynthesisEngine.extract_citations(text)
    assert len(cites) == 2
    assert any("PR #88" in c for c in cites)
    assert any("Commit e91c2bf" in c for c in cites)


def test_grounded_synthesis_validation() -> None:
    manifest = [
        EvidenceCitation(
            citation_key="[PR #88]",
            evidence_type=EvidenceType.PULL_REQUEST,
            identifier="88",
            title="feat: retry",
            confidence=1.0,
        ),
        EvidenceCitation(
            citation_key="[Commit e91c2bf]",
            evidence_type=EvidenceType.COMMIT,
            identifier="e91c2bf4a128",
            title="fix",
            confidence=0.95,
        ),
    ]

    valid_text = "Developer completed [PR #88] with HMAC in [Commit e91c2bf]."
    assert GroundedSynthesisEngine.validate_grounding(valid_text, manifest) is True

    # Hallucinated citation
    invalid_text = "Developer worked on [PR #9999] without any evidence."
    assert GroundedSynthesisEngine.validate_grounding(invalid_text, manifest) is False

    # Long text with zero citations
    ungrounded_text = "This is a very long claim about system architecture that has zero inline citations attached to it."
    assert GroundedSynthesisEngine.validate_grounding(ungrounded_text, manifest) is False


def test_generate_handoff_package_unit() -> None:
    work_item = WorkItem(
        id="wi_AUTH-101",
        organization_id="snapmeet",
        external_id="AUTH-101",
        project_key="AUTH",
        title="OAuth2 Gateway Integration",
        status=WorkItemStatus.DONE,
    )
    prs = [
        PullRequestEvent(
            organization_id="snapmeet",
            repo_name="snapmeet/auth-service",
            pr_number=42,
            title="feat: oauth2 gateway",
            state=PRStatus.OPEN,
            ci_status=CIStatus.FAILED,
            head_branch="feat/AUTH-101",
            author_login="dev-user",
            linked_issue_keys=["AUTH-101"],
        )
    ]
    commits = [
        CommitInfo(
            sha="a1b2c3d4e5f6789012345678901234567890abcd",
            message="AUTH-101: implement oauth2 tokens",
            author_name="Alice Chen",
            author_email="alice@snapmeet.com",
            files_changed=["auth/tokens.py"],
        )
    ]
    anomalies = [
        AnomalyRuleResult(
            rule_id="HW-03",
            anomaly_type=AnomalyType.HW_03,
            triggered=True,
            severity=AnomalySeverity.HIGH,
            summary="State Mismatch",
            description="Jira DONE but PR open",
            recommended_action="Fix CI",
        )
    ]

    package = GroundedSynthesisEngine.generate_handoff_package(
        work_item=work_item,
        pull_requests=prs,
        commits=commits,
        anomalies=anomalies,
        outgoing_dev_name="Alice Chen",
        incoming_dev_name="Bob Smith",
    )

    assert package.task_key == "AUTH-101"
    assert "[PR #42]" in package.briefing.overview
    assert len(package.anomalies) == 1
    assert len(package.briefing.action_checklist) == 1


def test_api_handoff_generate_endpoint_dynamic() -> None:
    token = create_access_token({
        "sub": "usr_bob",
        "email": "bob@snapmeet.com",
        "org_id": "snapmeet",
        "allowed_repos": ["snapmeet/auth-service"],
    })

    payload = {
        "organization_id": "snapmeet",
        "work_item": {
            "id": "wi_AUTH-101",
            "organization_id": "snapmeet",
            "external_id": "AUTH-101",
            "project_key": "AUTH",
            "title": "OAuth2 Gateway Integration",
            "status": "DONE",
        },
        "repo_id": "snapmeet/auth-service",
        "outgoing_developer": "Alice Chen",
        "incoming_developer": "Bob Smith",
        "pull_requests": [
            {
                "organization_id": "snapmeet",
                "repo_name": "snapmeet/auth-service",
                "pr_number": 42,
                "title": "feat: oauth2 [AUTH-101]",
                "state": "OPEN",
                "ci_status": "FAILED",
                "head_branch": "feat/AUTH-101",
                "author_login": "alice",
                "linked_issue_keys": ["AUTH-101"],
            }
        ],
        "commits": [
            {
                "sha": "a1b2c3d4e5f6789012345678901234567890abcd",
                "message": "AUTH-101: oauth tokens",
                "author_name": "Alice Chen",
                "author_email": "alice@snapmeet.com",
                "files_changed": ["auth/tokens.py"],
            }
        ],
    }

    response = client.post(
        "/api/v1/handoff/generate",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["task_key"] == "AUTH-101"
    assert "[PR #42]" in data["briefing"]["overview"]
    assert len(data["anomalies"]) > 0


def test_api_chat_query_endpoint_dynamic() -> None:
    token = create_access_token({
        "sub": "usr_bob",
        "email": "bob@snapmeet.com",
        "org_id": "snapmeet",
        "allowed_repos": ["snapmeet/auth-service"],
    })

    # Allowed query
    response = client.post(
        "/api/v1/chat/query",
        json={
            "organization_id": "snapmeet",
            "repo_id": "snapmeet/auth-service",
            "query": "Where are OAuth tokens parsed?",
            "context_keys": ["PR #42", "Commit a1b2c3d"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["access_granted"] is True
    assert "[PR #42]" in data["citations"]

    # Restricted repo query (AccessRestrictedError -> 403)
    response_restricted = client.post(
        "/api/v1/chat/query",
        json={
            "organization_id": "snapmeet",
            "repo_id": "snapmeet/executive-financials",
            "query": "What are the Q3 numbers?",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response_restricted.status_code == 403


def test_api_handoff_invalid_token() -> None:
    payload = {
        "organization_id": "snapmeet",
        "work_item": {
            "id": "wi_AUTH-101",
            "organization_id": "snapmeet",
            "external_id": "AUTH-101",
            "project_key": "AUTH",
            "title": "OAuth2 Gateway Integration",
            "status": "DONE",
        },
        "repo_id": "snapmeet/auth-service",
        "outgoing_developer": "Alice Chen",
        "incoming_developer": "Bob Smith",
    }
    response = client.post(
        "/api/v1/handoff/generate",
        json=payload,
        headers={"Authorization": "Bearer invalid_handoff_jwt"},
    )
    assert response.status_code == 401


def test_handoff_hw04_architecture_drift_populates_anomalies() -> None:
    token = create_access_token({
        "sub": "user_alice",
        "org_id": "snapmeet",
        "role": "MEMBER",
        "allowed_repos": ["snapmeet/auth-service"],
    })
    payload = {
        "organization_id": "snapmeet",
        "work_item": {
            "id": "wi_AUTH-101",
            "organization_id": "snapmeet",
            "external_id": "AUTH-101",
            "project_key": "AUTH",
            "title": "OAuth2 Gateway Integration",
            "status": "IN_PROGRESS",
        },
        "repo_id": "snapmeet/auth-service",
        "outgoing_developer": "Alice Chen",
        "incoming_developer": "Bob Smith",
        "commits": [],
        "pull_requests": [],
        "code_imported_services": ["payment-service", "auth-service", "audit-service"],
        "diagram_documented_services": ["auth-service"],
    }
    response = client.post(
        "/api/v1/handoff/generate",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "anomalies" in data
    hw04_anomalies = [a for a in data["anomalies"] if a["rule_id"] == "HW-04"]
    assert len(hw04_anomalies) == 1
    hw04 = hw04_anomalies[0]
    assert hw04["triggered"] is True
    assert set(hw04["affected_entities"]) == {"payment-service", "audit-service"}

    # Also verify the Celery worker task for HW-04
    from workers.tasks.diagram import evaluate_architecture_drift_task
    celery_result = evaluate_architecture_drift_task(
        organization_id="snapmeet",
        code_imported_services=["analytics-db", "auth-service"],
        diagram_documented_services=["auth-service"],
        task_key="AUTH-101",
    )
    assert celery_result["rule_id"] == "HW-04"
    assert celery_result["triggered"] is True
    assert "analytics-db" in celery_result["affected_entities"]




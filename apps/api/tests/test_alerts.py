from fastapi.testclient import TestClient
from packages.schemas.anomaly import AnomalyRuleResult, AnomalySeverity, AnomalyType
from workers.tasks.alerts import dispatch_anomaly_alert

from apps.api.app.core.security import create_access_token
from apps.api.app.main import app
from apps.api.app.services.slack_notifier import SlackAlertFormatter

client = TestClient(app)


def test_slack_alert_formatter() -> None:
    anomaly = AnomalyRuleResult(
        rule_id="HW-03",
        anomaly_type=AnomalyType.HW_03,
        triggered=True,
        severity=AnomalySeverity.HIGH,
        summary="State Mismatch",
        description="Jira DONE but PR #88 is open with CI failure.",
        recommended_action="Investigate settings.py",
    )

    card = SlackAlertFormatter.format_anomaly_card(
        organization_id="snapmeet",
        task_key="BILL-204",
        repo_id="snapmeet/billing-service",
        anomaly=anomaly,
    )

    assert "HW-03" in card["text"]
    assert len(card["blocks"]) >= 4
    assert card["blocks"][0]["type"] == "header"


def test_api_alerts_dispatch_endpoint() -> None:
    token = create_access_token({
        "sub": "usr_aman",
        "email": "aman@snapmeet.com",
        "org_id": "snapmeet",
        "allowed_repos": ["snapmeet/billing-service"],
    })

    payload = {
        "organization_id": "snapmeet",
        "task_key": "BILL-204",
        "repo_id": "snapmeet/billing-service",
        "anomaly": {
            "rule_id": "HW-03",
            "anomaly_type": AnomalyType.HW_03.value,
            "triggered": True,
            "severity": AnomalySeverity.HIGH.value,
            "summary": "State Mismatch",
            "description": "Jira marked DONE but PR open",
            "recommended_action": "Fix CI",
        },
    }

    response = client.post(
        "/api/v1/alerts/dispatch",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SUCCESS"
    assert data["dispatched"] is True
    assert "blocks" in data["formatted_payload"]


def test_celery_alert_task() -> None:
    anomaly_data = {
        "rule_id": "HW-01",
        "anomaly_type": AnomalyType.HW_01.value,
        "triggered": True,
        "severity": AnomalySeverity.MEDIUM.value,
        "summary": "Shadow Work",
        "description": "PR active without ticket",
        "recommended_action": "Create Jira ticket",
    }
    result = dispatch_anomaly_alert("snapmeet", "AUTH-101", "snapmeet/auth-service", anomaly_data)
    assert result["status"] == "DELIVERED"
    assert result["blocks_count"] >= 4


def test_api_alerts_dispatch_with_webhook_url(monkeypatch) -> None:
    import httpx

    token = create_access_token({
        "sub": "usr_aman",
        "email": "aman@snapmeet.com",
        "org_id": "snapmeet",
        "allowed_repos": ["snapmeet/billing-service"],
    })

    class MockResponse:
        status_code = 200

    async def mock_post(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    payload = {
        "organization_id": "snapmeet",
        "task_key": "BILL-204",
        "repo_id": "snapmeet/billing-service",
        "webhook_url": "https://hooks.slack.com/services/T00/B00/X00",
        "anomaly": {
            "rule_id": "HW-03",
            "anomaly_type": AnomalyType.HW_03.value,
            "triggered": True,
            "severity": AnomalySeverity.HIGH.value,
            "summary": "State Mismatch",
            "description": "Jira marked DONE but PR open",
            "recommended_action": "Fix CI",
        },
    }

    response = client.post(
        "/api/v1/alerts/dispatch",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["dispatched"] is True


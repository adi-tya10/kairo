import hashlib
import hmac
import json
from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.api.app.core.config import get_settings
from apps.api.app.main import app

client = TestClient(app)


def test_github_webhook_authenticated():
    settings = get_settings()
    payload = {
        "action": "opened",
        "number": 88,
        "pull_request": {
            "title": "feat: razorpay retry queue",
            "state": "open",
        },
        "organization": {"login": "snapmeet"},
    }
    raw_body = json.dumps(payload).encode("utf-8")
    secret = settings.GITHUB_WEBHOOK_SECRET.encode("utf-8")
    sig = "sha256=" + hmac.new(secret, raw_body, hashlib.sha256).hexdigest()

    with patch("workers.celery_app.celery_app.send_task") as mock_send:
        response = client.post(
            "/api/v1/webhooks/github",
            content=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "del_12345",
                "X-Hub-Signature-256": sig,
            },
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert data["provider"] == "github"
        assert data["delivery_id"] == "del_12345"
        mock_send.assert_called_once()


def test_github_webhook_unauthorized():
    payload = {"action": "opened"}
    raw_body = json.dumps(payload).encode("utf-8")

    response = client.post(
        "/api/v1/webhooks/github",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "del_12345",
            "X-Hub-Signature-256": "sha256=invalid_signature",
        },
    )
    assert response.status_code == 401


def test_jira_webhook_accepted():
    payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "BILL-204",
            "fields": {
                "summary": "Razorpay Invoicing Integration",
                "status": {"name": "Done"},
            },
        },
        "organization_id": "snapmeet",
    }
    raw_body = json.dumps(payload).encode("utf-8")

    with patch("workers.celery_app.celery_app.send_task") as mock_send:
        response = client.post(
            "/api/v1/webhooks/jira/snapmeet",
            content=raw_body,
            headers={
                "Content-Type": "application/json",
                "X-Atlassian-Webhook-Identifier": "jira_del_9988",
            },
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert data["provider"] == "jira"
        mock_send.assert_called_once()


def test_linear_webhook_accepted():
    payload = {
        "action": "create",
        "data": {
            "identifier": "ENG-402",
            "title": "Implement Stripe tax calculation idempotency",
            "state": {"name": "In Progress"},
            "assignee": {"name": "Rahul Sharma", "email": "rahul@snapmeet.com"},
        },
    }
    with patch("workers.celery_app.celery_app.send_task") as mock_send:
        response = client.post(
            "/api/v1/webhooks/linear/snapmeet",
            json=payload,
            headers={"Linear-Event": "Issue", "Linear-Delivery": "del_lin_1"},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert data["provider"] == "linear"
        mock_send.assert_called_once()


def test_gitlab_webhook_accepted():
    payload = {
        "object_kind": "merge_request",
        "project": {"name": "billing-service", "path_with_namespace": "snapmeet/billing-service"},
        "object_attributes": {"iid": 18, "title": "Resolve checkout retry [BILL-204]", "state": "opened"},
    }
    with patch("workers.celery_app.celery_app.send_task") as mock_send:
        response = client.post(
            "/api/v1/webhooks/gitlab/snapmeet",
            json=payload,
            headers={"X-Gitlab-Event": "Merge Request Hook"},
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        assert data["provider"] == "gitlab"
        mock_send.assert_called_once()


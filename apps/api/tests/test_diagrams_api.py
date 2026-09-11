from fastapi.testclient import TestClient

from apps.api.app.core.security import create_access_token
from apps.api.app.main import app
from workers.tasks.diagram import process_diagram_document

client = TestClient(app)


def _get_token(org_id: str = "snapmeet") -> str:
    return create_access_token({
        "sub": "usr_diagram_tester",
        "email": "tester@snapmeet.com",
        "org_id": org_id,
        "is_org_admin": True,
        "allowed_repos": [f"{org_id}/primary-repo"],
    })


def test_api_diagram_parse_endpoint() -> None:
    payload = {
        "filename": "architecture_spec.txt",
        "content": "[Billing Service]\n[Redis Cache]\n[PostgreSQL DB]\n",
    }

    # 1. Unauthenticated request rejected with 401
    res_unauth = client.post(
        "/api/v1/diagrams/parse",
        json=payload,
    )
    assert res_unauth.status_code == 401

    # 2. Authenticated request succeeds
    token = _get_token("snapmeet")
    response = client.post(
        "/api/v1/diagrams/parse",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "architecture_spec.txt"
    assert data["component_count"] == 3
    labels = [c["label"] for c in data["components"]]
    assert "Billing Service" in labels
    assert "Redis Cache" in labels


def test_celery_diagram_task() -> None:
    raw_text = "[Payment Gateway]\n[Stripe Webhook Listener]"
    result = process_diagram_document(raw_text, "doc_99")
    assert result["document_id"] == "doc_99"
    assert result["component_count"] == 2

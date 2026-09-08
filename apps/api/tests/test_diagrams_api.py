from fastapi.testclient import TestClient
from workers.tasks.diagram import process_diagram_document

from apps.api.app.main import app

client = TestClient(app)


def test_api_diagram_parse_endpoint() -> None:
    payload = {
        "filename": "architecture_spec.txt",
        "content": "[Billing Service]\n[Redis Cache]\n[PostgreSQL DB]\n",
    }

    response = client.post(
        "/api/v1/diagrams/parse",
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

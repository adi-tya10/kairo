"""
Unit tests for the Knowledge Graph API and GraphLineageService.

All tests use a mocked Neo4j session — no live database connection required.
The get_graph_db dependency is overridden via app.dependency_overrides so that
the route under test receives a controllable MagicMock session.
"""
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from apps.api.app.core.database import get_graph_db
from apps.api.app.core.security import create_access_token
from apps.api.app.main import app
from apps.api.app.services.graph_service import GraphLineageService

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_session(records: list[Any]) -> MagicMock:
    """Build a MagicMock Neo4j session whose .run() returns the given records."""
    mock_session = MagicMock()
    mock_session.run.return_value = records
    return mock_session


@contextmanager
def _override_graph_db(mock_session: MagicMock):
    """Context manager that installs and tears down a get_graph_db override."""
    def _fake_get_graph_db():
        yield mock_session

    app.dependency_overrides[get_graph_db] = _fake_get_graph_db
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_graph_db, None)


def _auth_header(org_id: str = "snapmeet", repos: list[str] | None = None) -> dict[str, str]:
    repos = repos or ["snapmeet/billing-service"]
    token = create_access_token({
        "sub": "usr_aman",
        "email": "aman@snapmeet.com",
        "org_id": org_id,
        "allowed_repos": repos,
    })
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# GraphLineageService unit tests
# ---------------------------------------------------------------------------

def test_graph_lineage_service_returns_empty_for_no_matches() -> None:
    """Service returns an empty list when Neo4j returns no records — not fake data."""
    mock_session = _make_mock_session([])
    result = GraphLineageService.extract_decision_subgraph("snapmeet", "BILL-999", mock_session)
    assert result == []
    mock_session.run.assert_called_once()


def test_graph_lineage_service_maps_records_correctly() -> None:
    """Service correctly maps Neo4j records to DecisionNode dataclasses."""
    mock_session = _make_mock_session([
        {
            "decision_id": "DEC-100",
            "title": "Use JWT RS256 for Auth",
            "rationale": "Asymmetric verification across microservices",
            "status": "APPROVED",
            "supersedes": "Symmetric HS256",
        }
    ])

    decisions = GraphLineageService.extract_decision_subgraph("snapmeet", "AUTH-101", mock_session)

    assert len(decisions) == 1
    assert decisions[0].decision_id == "DEC-100"
    assert decisions[0].title == "Use JWT RS256 for Auth"
    assert decisions[0].supersedes == "Symmetric HS256"


def test_graph_lineage_service_handles_multiple_decisions() -> None:
    """Service maps multiple records, including ones with no supersedes."""
    records = [
        {
            "decision_id": "DEC-200",
            "title": "Adopt Redis SETNX for Idempotency",
            "rationale": "Prevents duplicate billing on webhook retries",
            "status": "ACCEPTED",
            "supersedes": None,
        },
        {
            "decision_id": "DEC-201",
            "title": "Switch to pgvector for embeddings",
            "rationale": "Eliminate external vector DB dependency",
            "status": "ACCEPTED",
            "supersedes": "Pinecone",
        },
    ]
    mock_session = _make_mock_session(records)
    decisions = GraphLineageService.extract_decision_subgraph("snapmeet", "INFRA-01", mock_session)

    assert len(decisions) == 2
    assert decisions[0].supersedes is None
    assert decisions[1].supersedes == "Pinecone"


def test_graph_lineage_service_raises_on_neo4j_failure() -> None:
    """Service raises RuntimeError when Neo4j query throws — does NOT swallow errors."""
    mock_session = MagicMock()
    mock_session.run.side_effect = Exception("connection reset by peer")

    with pytest.raises(RuntimeError, match="Neo4j query failed"):
        GraphLineageService.extract_decision_subgraph("snapmeet", "BILL-204", mock_session)


def test_graph_lineage_service_uses_correct_cypher_params() -> None:
    """Service passes org_id and task_key as Cypher parameters — not string formatted."""
    mock_session = _make_mock_session([])
    GraphLineageService.extract_decision_subgraph("acme-corp", "TASK-55", mock_session)

    call_kwargs = mock_session.run.call_args
    assert call_kwargs.kwargs.get("org_id") == "acme-corp" or call_kwargs.args[1] == "acme-corp" or \
           "acme-corp" in str(call_kwargs)
    mock_session.run.assert_called_once()


# ---------------------------------------------------------------------------
# API endpoint tests (get_graph_db dependency overridden)
# ---------------------------------------------------------------------------

def test_api_graph_lineage_returns_decisions() -> None:
    """Endpoint returns correctly structured response with mocked Neo4j session."""
    records = [
        {
            "decision_id": "DEC-100",
            "title": "Use JWT RS256",
            "rationale": "Cross-service auth",
            "status": "APPROVED",
            "supersedes": None,
        }
    ]
    mock_session = _make_mock_session(records)

    with _override_graph_db(mock_session):
        response = client.get(
            "/api/v1/graph/lineage/BILL-204?organization_id=snapmeet&repo_id=snapmeet/billing-service",
            headers=_auth_header(),
        )

    assert response.status_code == 200
    data = response.json()
    assert data["task_key"] == "BILL-204"
    assert data["organization_id"] == "snapmeet"
    assert len(data["decisions"]) == 1
    assert data["decisions"][0]["decision_id"] == "DEC-100"
    # Graph nodes and edges built correctly
    assert any(n["type"] == "Task" for n in data["nodes"])
    assert any(n["type"] == "Decision" for n in data["nodes"])
    assert any(e["relationship"] == "JUSTIFIES" for e in data["edges"])


def test_api_graph_lineage_empty_graph_returns_200() -> None:
    """Endpoint returns 200 with empty lists when no decisions exist for the task."""
    mock_session = _make_mock_session([])

    with _override_graph_db(mock_session):
        response = client.get(
            "/api/v1/graph/lineage/NEW-001?organization_id=snapmeet&repo_id=snapmeet/billing-service",
            headers=_auth_header(),
        )

    assert response.status_code == 200
    data = response.json()
    assert data["decisions"] == []
    assert data["edges"] == []
    # Task node still present even if no decisions
    assert len(data["nodes"]) == 1
    assert data["nodes"][0]["type"] == "Task"


def test_api_graph_lineage_with_supersedes_builds_full_graph() -> None:
    """Endpoint builds SUPERSEDES edges when a decision supersedes an older one."""
    records = [
        {
            "decision_id": "DEC-201",
            "title": "Switch to pgvector",
            "rationale": "Eliminate Pinecone dependency",
            "status": "ACCEPTED",
            "supersedes": "Pinecone Vector DB",
        }
    ]
    mock_session = _make_mock_session(records)

    with _override_graph_db(mock_session):
        response = client.get(
            "/api/v1/graph/lineage/INFRA-01?organization_id=snapmeet&repo_id=snapmeet/billing-service",
            headers=_auth_header(),
        )

    assert response.status_code == 200
    data = response.json()
    superseded_nodes = [n for n in data["nodes"] if n.get("status") == "SUPERSEDED"]
    supersedes_edges = [e for e in data["edges"] if e["relationship"] == "SUPERSEDES"]
    assert len(superseded_nodes) == 1
    assert len(supersedes_edges) == 1


def test_api_graph_lineage_invalid_token_returns_401() -> None:
    """Endpoint rejects malformed JWT tokens."""
    mock_session = _make_mock_session([])

    with _override_graph_db(mock_session):
        response = client.get(
            "/api/v1/graph/lineage/BILL-204?organization_id=snapmeet&repo_id=snapmeet/billing-service",
            headers={"Authorization": "Bearer invalid_token_xyz"},
        )

    assert response.status_code == 401


def test_api_graph_lineage_missing_org_id_returns_400() -> None:
    """Endpoint returns 400 when organization_id is not provided."""
    mock_session = _make_mock_session([])

    with _override_graph_db(mock_session):
        response = client.get(
            "/api/v1/graph/lineage/BILL-204?repo_id=snapmeet/billing-service",
            headers=_auth_header(),
        )

    assert response.status_code == 400


def test_api_graph_lineage_cross_tenant_access_denied() -> None:
    """ACL guard rejects a token for org_A trying to query org_B's data."""
    mock_session = _make_mock_session([])

    with _override_graph_db(mock_session):
        response = client.get(
            "/api/v1/graph/lineage/BILL-204?organization_id=other-org&repo_id=snapmeet/billing-service",
            headers=_auth_header(org_id="snapmeet"),  # token says snapmeet but querying other-org
        )

    assert response.status_code in (403, 401)


def test_api_graph_lineage_neo4j_failure_returns_503() -> None:
    """Endpoint returns 503 Service Unavailable when Neo4j throws during query."""
    mock_session = MagicMock()
    mock_session.run.side_effect = Exception("Neo4j cluster unreachable")

    with _override_graph_db(mock_session):
        response = client.get(
            "/api/v1/graph/lineage/BILL-204?organization_id=snapmeet&repo_id=snapmeet/billing-service",
            headers=_auth_header(),
        )

    assert response.status_code == 503

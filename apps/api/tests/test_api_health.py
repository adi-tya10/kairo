"""
Unit tests for health endpoints.
Both check_database_health and check_neo4j_health are mocked so these tests
run without any real database connectivity.
"""
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from apps.api.app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "KAIRO" in data["engine"]


def test_health_endpoint_all_healthy():
    """Both dependencies healthy → status == 'healthy'."""
    with (
        patch("apps.api.app.api.v1.health.check_database_health", new=AsyncMock(return_value=True)),
        patch("apps.api.app.api.v1.health.check_neo4j_health", new=AsyncMock(return_value=True)),
    ):
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "kairo-api"
    assert data["postgresql"] is True
    assert data["neo4j_graph"] is True


def test_health_endpoint_neo4j_degraded():
    """Neo4j unreachable → status == 'degraded', postgresql still True."""
    with (
        patch("apps.api.app.api.v1.health.check_database_health", new=AsyncMock(return_value=True)),
        patch("apps.api.app.api.v1.health.check_neo4j_health", new=AsyncMock(return_value=False)),
    ):
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["postgresql"] is True
    assert data["neo4j_graph"] is False


def test_health_endpoint_postgres_degraded():
    """PostgreSQL unreachable → status == 'degraded'."""
    with (
        patch("apps.api.app.api.v1.health.check_database_health", new=AsyncMock(return_value=False)),
        patch("apps.api.app.api.v1.health.check_neo4j_health", new=AsyncMock(return_value=True)),
    ):
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["postgresql"] is False
    assert data["neo4j_graph"] is True


def test_health_endpoint_all_degraded():
    """Both dependencies down → status == 'degraded'."""
    with (
        patch("apps.api.app.api.v1.health.check_database_health", new=AsyncMock(return_value=False)),
        patch("apps.api.app.api.v1.health.check_neo4j_health", new=AsyncMock(return_value=False)),
    ):
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"


def test_api_v1_health_endpoint():
    """/api/v1/health is also reachable and returns the same structure."""
    with (
        patch("apps.api.app.api.v1.health.check_database_health", new=AsyncMock(return_value=True)),
        patch("apps.api.app.api.v1.health.check_neo4j_health", new=AsyncMock(return_value=True)),
    ):
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

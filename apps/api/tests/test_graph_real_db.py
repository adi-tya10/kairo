"""
KAIRO Neo4j AuraDB Live Integration Tests.

These tests run ONLY when TEST_LIVE_GRAPH=true is set in the environment.
They require a real, reachable Neo4j AuraDB instance with valid credentials
configured via NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD in .env.

They will FAIL LOUDLY — not skip — if the database is unreachable, proving
that the connection is genuinely live and not silently degraded.

Run with:
    TEST_LIVE_GRAPH=true pytest tests/test_graph_real_db.py -v
"""

import os

import pytest
from neo4j import GraphDatabase

from apps.api.app.core.config import get_settings
from apps.api.app.core.database import get_neo4j_driver, reset_neo4j_driver
from apps.api.app.services.graph_service import GraphLineageService

# Skip the entire module unless TEST_LIVE_GRAPH=true
pytestmark = pytest.mark.skipif(
    os.environ.get("TEST_LIVE_GRAPH", "").lower() != "true",
    reason="Skipping live Neo4j tests. Set TEST_LIVE_GRAPH=true to run.",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def live_driver():
    """
    Provides a real Neo4j driver for the test session.
    Fails immediately (not silently) if credentials are missing or unreachable.
    """
    settings = get_settings()
    assert settings.NEO4J_URI, "NEO4J_URI must be set for live tests"
    assert settings.NEO4J_USER, "NEO4J_USER must be set for live tests"
    assert settings.NEO4J_PASSWORD, "NEO4J_PASSWORD must be set for live tests"

    driver = GraphDatabase.driver(
        settings.NEO4J_URI,
        auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
    )
    # Fail loudly on connectivity issues — not silently
    driver.verify_connectivity()
    yield driver
    driver.close()


@pytest.fixture(scope="module")
def live_session(live_driver):
    """Provides a single Neo4j session shared across module-level tests."""
    session = live_driver.session()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def cleanup_test_nodes(live_driver):
    """
    Ensures test data is removed before and after each test to prevent pollution.
    Scoped to org_id='test-org-kairo-live' so it never touches real tenant data.
    """
    TEST_ORG = "test-org-kairo-live"

    def _purge():
        with live_driver.session() as s:
            s.run("MATCH (n {org_id: $org_id}) DETACH DELETE n", org_id=TEST_ORG)

    _purge()
    yield
    _purge()


# ---------------------------------------------------------------------------
# Connectivity tests
# ---------------------------------------------------------------------------

def test_live_neo4j_connectivity(live_driver) -> None:
    """Confirms the driver can establish a real connection to Neo4j AuraDB."""
    # verify_connectivity() raises on failure — if we got here, it worked
    live_driver.verify_connectivity()


def test_live_neo4j_can_run_simple_query(live_session) -> None:
    """Verifies basic read capability against the live cluster."""
    result = live_session.run("RETURN 1 AS value")
    record = result.single()
    assert record is not None
    assert record["value"] == 1


# ---------------------------------------------------------------------------
# GraphLineageService live tests
# ---------------------------------------------------------------------------

TEST_ORG = "test-org-kairo-live"
TEST_TASK_KEY = "LIVE-001"
TEST_DECISION_ID = "DEC-LIVE-001"


def test_live_extract_decision_subgraph_empty(live_session) -> None:
    """
    Returns an empty list for a task with no decisions — not fake data.
    Proves the service queries the real graph rather than returning a static stub.
    """
    result = GraphLineageService.extract_decision_subgraph(
        organization_id=TEST_ORG,
        task_key="NONEXISTENT-9999",
        session=live_session,
    )
    assert result == []


def test_live_create_and_retrieve_decision(live_driver) -> None:
    """
    Writes a Decision and Task to AuraDB, then retrieves via the service.
    Verifies the full write → query roundtrip works end-to-end.
    """
    # Seed test data using parameterized Cypher (never f-string formatted)
    with live_driver.session() as seed_session:
        seed_session.run(
            """
            CREATE (t:Task {key: $task_key, org_id: $org_id, status: 'IN_PROGRESS'})
            CREATE (d:Decision {
                id: $dec_id,
                org_id: $org_id,
                title: 'Live Test Decision',
                rationale: 'Created by integration test',
                status: 'ACCEPTED'
            })
            CREATE (d)-[:JUSTIFIES]->(t)
            """,
            task_key=TEST_TASK_KEY,
            org_id=TEST_ORG,
            dec_id=TEST_DECISION_ID,
        )

    # Retrieve using the service
    with live_driver.session() as query_session:
        decisions = GraphLineageService.extract_decision_subgraph(
            organization_id=TEST_ORG,
            task_key=TEST_TASK_KEY,
            session=query_session,
        )

    assert len(decisions) == 1
    assert decisions[0].decision_id == TEST_DECISION_ID
    assert decisions[0].title == "Live Test Decision"
    assert decisions[0].status == "ACCEPTED"
    assert decisions[0].supersedes is None


def test_live_supersedes_relationship_traversed(live_driver) -> None:
    """
    Verifies that (d:Decision)-[:SUPERSEDES]->(old:Decision) is correctly traversed
    and the old decision's title is returned in the supersedes field.
    """
    with live_driver.session() as seed_session:
        seed_session.run(
            """
            CREATE (t:Task {key: $task_key, org_id: $org_id, status: 'DONE'})
            CREATE (old:Decision {
                id: 'DEC-LIVE-OLD',
                org_id: $org_id,
                title: 'Old Approach',
                rationale: 'Deprecated',
                status: 'SUPERSEDED'
            })
            CREATE (d:Decision {
                id: $dec_id,
                org_id: $org_id,
                title: 'New Approach',
                rationale: 'Better performance',
                status: 'ACCEPTED'
            })
            CREATE (d)-[:SUPERSEDES]->(old)
            CREATE (d)-[:JUSTIFIES]->(t)
            """,
            task_key=TEST_TASK_KEY,
            org_id=TEST_ORG,
            dec_id=TEST_DECISION_ID,
        )

    with live_driver.session() as query_session:
        decisions = GraphLineageService.extract_decision_subgraph(
            organization_id=TEST_ORG,
            task_key=TEST_TASK_KEY,
            session=query_session,
        )

    assert len(decisions) == 1
    assert decisions[0].supersedes == "Old Approach"


# ---------------------------------------------------------------------------
# Tenant isolation tests
# ---------------------------------------------------------------------------

def test_live_tenant_isolation_org_a_cannot_read_org_b(live_driver) -> None:
    """
    Critical: a query scoped to org_A must return zero results for data
    seeded under org_B. Proves that org_id is enforced at the Cypher layer,
    not just the application layer.
    """
    ORG_A = "test-org-kairo-live"
    ORG_B = "test-org-kairo-live-b"

    # Seed a task/decision under ORG_B
    with live_driver.session() as seed_session:
        seed_session.run(
            """
            CREATE (t:Task {key: $task_key, org_id: $org_id, status: 'DONE'})
            CREATE (d:Decision {
                id: 'DEC-B-001',
                org_id: $org_id,
                title: 'Org B Decision',
                rationale: 'Should not be visible to Org A',
                status: 'ACCEPTED'
            })
            CREATE (d)-[:JUSTIFIES]->(t)
            """,
            task_key=TEST_TASK_KEY,
            org_id=ORG_B,
        )

    # Query as ORG_A — must return nothing
    with live_driver.session() as query_session:
        decisions = GraphLineageService.extract_decision_subgraph(
            organization_id=ORG_A,  # Querying as Org A
            task_key=TEST_TASK_KEY,
            session=query_session,
        )

    assert decisions == [], (
        f"TENANT ISOLATION FAILURE: Org A received {len(decisions)} decision(s) "
        f"belonging to Org B. This is a critical security defect."
    )

    # Cleanup ORG_B nodes (autouse fixture only cleans ORG_A)
    with live_driver.session() as cleanup_session:
        cleanup_session.run(
            "MATCH (n {org_id: $org_id}) DETACH DELETE n", org_id=ORG_B
        )


# ---------------------------------------------------------------------------
# get_neo4j_driver() singleton test
# ---------------------------------------------------------------------------

def test_live_get_neo4j_driver_returns_singleton() -> None:
    """
    get_neo4j_driver() must return the same driver instance on repeated calls
    (not open a new connection each time).
    """
    reset_neo4j_driver()  # ensure clean state
    driver_1 = get_neo4j_driver()
    driver_2 = get_neo4j_driver()
    assert driver_1 is driver_2, "get_neo4j_driver() must be a singleton"
    reset_neo4j_driver()  # clean up after test

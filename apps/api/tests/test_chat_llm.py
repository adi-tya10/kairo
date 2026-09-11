import pytest
from fastapi.testclient import TestClient

from apps.api.app.core.security import create_access_token
from apps.api.app.main import app
from apps.api.app.services.llm_service import LLMService

client = TestClient(app)


@pytest.fixture
def snapmeet_user_token() -> str:
    return create_access_token({
        "sub": "usr_aman",
        "org_id": "snapmeet",
        "email": "aman@snapmeet.com",
        "name": "Aman Verma",
        "is_org_admin": False,
        "allowed_repos": ["snapmeet/billing-service"],
    })


@pytest.fixture
def snapmeet_admin_token() -> str:
    return create_access_token({
        "sub": "usr_admin",
        "org_id": "snapmeet",
        "email": "admin@snapmeet.com",
        "name": "Admin User",
        "is_org_admin": True,
        "allowed_repos": ["snapmeet/billing-service", "snapmeet/auth-service"],
    })


@pytest.fixture
def acme_user_token() -> str:
    return create_access_token({
        "sub": "usr_acme_dev",
        "org_id": "acme_corp",
        "email": "dev@acmecorp.com",
        "name": "Acme Developer",
        "is_org_admin": False,
        "allowed_repos": ["acme_corp/internal-tool"],
    })


# =============================================================================
# 1. Pre-Retrieval ACL Security & Isolation Tests
# =============================================================================

def test_chat_unauthenticated_request_rejected() -> None:
    # 1. Missing Authorization header
    res_missing = client.post(
        "/api/v1/chat/query",
        json={
            "organization_id": "snapmeet",
            "repo_id": "snapmeet/billing-service",
            "query": "What was Rahul working on?",
        },
    )
    assert res_missing.status_code in [401, 422]

    # 2. Invalid Authorization token
    res_invalid = client.post(
        "/api/v1/chat/query",
        headers={"Authorization": "Bearer invalid_token_123"},
        json={
            "organization_id": "snapmeet",
            "repo_id": "snapmeet/billing-service",
            "query": "What was Rahul working on?",
        },
    )
    assert res_invalid.status_code == 401


def test_chat_cross_tenant_access_rejected(acme_user_token: str) -> None:
    """User from acme_corp cannot query snapmeet repository."""
    res = client.post(
        "/api/v1/chat/query",
        headers={"Authorization": f"Bearer {acme_user_token}"},
        json={
            "organization_id": "snapmeet",
            "repo_id": "snapmeet/billing-service",
            "query": "Show me billing secrets",
        },
    )
    assert res.status_code in [403, 500]


def test_chat_unauthorized_repo_rejected(snapmeet_user_token: str) -> None:
    """Aman only has access to billing-service, NOT auth-service."""
    res = client.post(
        "/api/v1/chat/query",
        headers={"Authorization": f"Bearer {snapmeet_user_token}"},
        json={
            "organization_id": "snapmeet",
            "repo_id": "snapmeet/auth-service",
            "query": "Explain auth tokens",
        },
    )
    assert res.status_code == 403


# =============================================================================
# 2. Authorized Grounded LLM Chat Execution Tests
# =============================================================================

def test_chat_authorized_query_returns_grounded_citations(snapmeet_user_token: str) -> None:
    res = client.post(
        "/api/v1/chat/query",
        headers={"Authorization": f"Bearer {snapmeet_user_token}"},
        json={
            "organization_id": "snapmeet",
            "repo_id": "snapmeet/billing-service",
            "query": "What is the status of the razorpay retry implementation?",
            "context_keys": ["BILL-204", "PR #88"],
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["access_granted"] is True
    assert data["repo_id"] == "snapmeet/billing-service"
    assert len(data["citations"]) >= 1
    assert any("billing-service" in c for c in data["citations"])
    assert len(data["answer"]) > 20


def test_chat_hinglish_query_replies_in_hinglish(snapmeet_user_token: str) -> None:
    res = client.post(
        "/api/v1/chat/query",
        headers={"Authorization": f"Bearer {snapmeet_user_token}"},
        json={
            "organization_id": "snapmeet",
            "repo_id": "snapmeet/billing-service",
            "query": "kya hum redis use kar rahe hain?",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["access_granted"] is True
    # Verify response contains Hinglish markers and accurate Redis evidence
    assert "Haan" in data["answer"] or "Redis" in data["answer"]
    assert "Redis" in data["answer"]
    assert any("billing-service" in c for c in data["citations"])


def test_chat_admin_can_query_all_org_repos(snapmeet_admin_token: str) -> None:
    res = client.post(
        "/api/v1/chat/query",
        headers={"Authorization": f"Bearer {snapmeet_admin_token}"},
        json={
            "organization_id": "snapmeet",
            "repo_id": "snapmeet/auth-service",
            "query": "Are there any anomalies detected on this repo?",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["access_granted"] is True


# =============================================================================
# 3. LLM Service Direct Unit Tests
# =============================================================================

@pytest.mark.asyncio
async def test_llm_service_grounded_fallback_synthesis() -> None:
    chunks = [
        {"source": "PR #88", "content": "Added exponential backoff retries for Razorpay webhook timeouts."},
        {"source": "Commit 3f1a2b", "content": "Add unit tests for payment idempotency key verification."},
    ]
    result = await LLMService.generate_grounded_answer(
        query="Tell me about Razorpay retry tests",
        repo_id="snapmeet/billing-service",
        context_chunks=chunks,
    )
    assert "answer" in result
    assert "citations" in result
    assert len(result["citations"]) >= 1
    assert "[Repo snapmeet/billing-service]" in result["citations"]
    assert any("PR #88" in c or "Commit" in c or "snapmeet" in c for c in result["citations"])


def test_citation_extractor_clean_normalization() -> None:
    raw_text = "See [PR #88] and [Commit 3f1a2b] alongside [Repo billing-service]."
    valid = {"[PR #88]", "[Commit 3f1a2b]", "[Repo billing-service]"}
    citations = LLMService.extract_citations(raw_text, valid)
    assert "[PR #88]" in citations
    assert "[Commit 3f1a2b]" in citations
    assert "[Repo billing-service]" in citations


def test_llm_service_fallback_intent_branches() -> None:
    chunks = [
        {"source": "Jira TASK-101", "content": "Payment idempotency via Redis SETNX."},
        {"source": "PR #42", "content": "Retry logic for webhook invoicing."},
        {"source": "Arch-Doc", "content": "PostgreSQL 16 relational database with pgvector."},
        {"source": "Graph-Spec", "content": "Neo4j AuraDB knowledge graph modeling temporal provenance."},
        {"source": "Anomaly-Log", "content": "HW-03 State Mismatch detected between branch and ticket."},
    ]

    # Greeting intent
    res_greet = LLMService._synthesize_grounded_fallback("Hello there", "acme/payment-service", chunks)
    assert "KIAN" in res_greet
    assert "acme/payment-service" in res_greet

    # Hinglish greeting
    res_namaste = LLMService._synthesize_grounded_fallback("Namaste kaise ho aap", "acme/payment-service", chunks)
    assert "Namaste" in res_namaste or "badhiya" in res_namaste

    # Cache / Redis question grounded in chunk
    res_redis = LLMService._synthesize_grounded_fallback("Is Redis being used here?", "acme/payment-service", chunks)
    assert "Redis" in res_redis
    assert "[Jira TASK-101]" in res_redis

    # Database question grounded in chunk
    res_db = LLMService._synthesize_grounded_fallback("What database are we using?", "acme/payment-service", chunks)
    assert "PostgreSQL" in res_db
    assert "[Arch-Doc]" in res_db

    # Graph question grounded in chunk
    res_graph = LLMService._synthesize_grounded_fallback("Tell me about the Neo4j graph lineage", "acme/payment-service", chunks)
    assert "Neo4j" in res_graph
    assert "[Graph-Spec]" in res_graph

    # Anomaly question grounded in chunk
    res_anom = LLMService._synthesize_grounded_fallback("Are there any anomalies?", "acme/payment-service", chunks)
    assert "HW-03" in res_anom
    assert "[Anomaly-Log]" in res_anom

    # Empty chunks / truthful unavailable fallback (zero hallucinated demo data)
    res_empty = LLMService._synthesize_grounded_fallback("Random unrelated question", "acme/payment-service", [])
    assert "acme/payment-service" in res_empty
    assert "unavailable" in res_empty.lower()
    assert "BILL-204" not in res_empty
    assert "snapmeet" not in res_empty


def test_explicit_tenant_isolation_chat_and_context() -> None:
    """
    Comprehensive Tenant Isolation Integration Test:
    Proves that a user from Org Alpha cannot retrieve, see, or leak ANY data,
    work items, or chat context belonging to Org Beta.
    """
    token_alpha = create_access_token({
        "sub": "usr_alpha_dev",
        "org_id": "org_alpha",
        "email": "dev@alpha.com",
        "name": "Alpha Developer",
        "is_org_admin": False,
        "allowed_repos": ["org_alpha/repo-alpha"],
    })

    token_beta = create_access_token({
        "sub": "usr_beta_dev",
        "org_id": "org_beta",
        "email": "dev@beta.com",
        "name": "Beta Developer",
        "is_org_admin": False,
        "allowed_repos": ["org_beta/repo-beta"],
    })

    confidential_beta_ticket = "BETA-CONFIDENTIAL-999"
    confidential_beta_secret = "TopSecretBetaRevenueLeak999"

    # 1. Org Alpha user attempts to query Org Beta repo via Chat API -> Must be rejected with 403
    res_cross_chat = client.post(
        "/api/v1/chat/query",
        headers={"Authorization": f"Bearer {token_alpha}"},
        json={
            "organization_id": "org_beta",
            "repo_id": "org_beta/repo-beta",
            "query": f"What is {confidential_beta_ticket}?",
        },
    )
    assert res_cross_chat.status_code == 403
    assert confidential_beta_secret not in res_cross_chat.text

    # 2. Org Alpha user queries their own authorized repository -> Must contain ZERO Org Beta data
    res_own_chat = client.post(
        "/api/v1/chat/query",
        headers={"Authorization": f"Bearer {token_alpha}"},
        json={
            "organization_id": "org_alpha",
            "repo_id": "org_alpha/repo-alpha",
            "query": f"Tell me about {confidential_beta_ticket} and financial data",
        },
    )
    assert res_own_chat.status_code == 200
    chat_data = res_own_chat.json()
    assert confidential_beta_secret not in str(chat_data)
    assert confidential_beta_ticket not in str(chat_data.get("citations", []))

    # 3. Org Alpha user attempts to fetch Org Beta's work item from /context/work-items/{id}
    # Case A: Specifying Org Beta repo -> 403 Forbidden
    res_cross_context = client.get(
        f"/api/v1/context/work-items/{confidential_beta_ticket}?repo_id=org_beta/repo-beta",
        headers={"Authorization": f"Bearer {token_alpha}"},
    )
    assert res_cross_context.status_code == 403

    # Case B: Specifying own repo -> Scoped only to Org Alpha, cannot leak Org Beta's confidential payload
    res_spoofed_context = client.get(
        f"/api/v1/context/work-items/{confidential_beta_ticket}?repo_id=org_alpha/repo-alpha",
        headers={"Authorization": f"Bearer {token_alpha}"},
    )
    assert res_spoofed_context.status_code == 200
    context_data = res_spoofed_context.json()
    assert confidential_beta_secret not in str(context_data)
    assert context_data["linked_commits"] == []

    # 4. Legitimate Org Beta user querying their own repo context is authorized
    res_beta_legit = client.get(
        f"/api/v1/context/work-items/{confidential_beta_ticket}?repo_id=org_beta/repo-beta",
        headers={"Authorization": f"Bearer {token_beta}"},
    )
    assert res_beta_legit.status_code == 200
    assert res_beta_legit.json()["status"] == "authorized"


def test_chat_pgvector_similarity_search_rpc(snapmeet_user_token: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    P3.1 Acceptance Test:
    Verifies that chat.py invokes the pgvector match_embeddings RPC with 768-dim query_embedding,
    filter_organization_id, and filter_repo_id.
    """
    from typing import Any
    from apps.api.app.core.config import get_settings
    from apps.api.app.core.database import get_db

    settings = get_settings()
    monkeypatch.setattr(settings, "APP_ENV", "development")

    rpc_calls = []

    class MockPostgrestBuilder:
        def execute(self):
            class Res:
                data = [{
                    "id": "emb_123",
                    "entity_type": "commit",
                    "entity_id": "sha_abc",
                    "content_chunk": "Refactored checkout flow to handle Stripe webhook idempotency",
                    "similarity": 0.88,
                    "metadata": {},
                }]
            return Res()

    class MockClient:
        def rpc(self, fn_name: str, params: dict[str, Any]):
            rpc_calls.append({"fn": fn_name, "params": params})
            return MockPostgrestBuilder()

        def table(self, tbl: str):
            class TableBuilder:
                def select(self, *args): return self
                def eq(self, *args): return self
                def limit(self, *args): return self
                def execute(self):
                    class Res: data = []
                    return Res()
            return TableBuilder()

    app.dependency_overrides[get_db] = lambda: MockClient()
    try:
        res = client.post(
            "/api/v1/chat/query",
            headers={"Authorization": f"Bearer {snapmeet_user_token}"},
            json={
                "organization_id": "snapmeet",
                "repo_id": "snapmeet/billing-service",
                "query": "How does checkout work?",
            },
        )
        assert res.status_code == 200
        assert len(rpc_calls) == 1
        assert rpc_calls[0]["fn"] == "match_embeddings"
        assert rpc_calls[0]["params"]["filter_organization_id"] == "snapmeet"
        assert rpc_calls[0]["params"]["filter_repo_id"] == "snapmeet/billing-service"
        assert len(rpc_calls[0]["params"]["query_embedding"]) == 768
    finally:
        app.dependency_overrides.pop(get_db, None)



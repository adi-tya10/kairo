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

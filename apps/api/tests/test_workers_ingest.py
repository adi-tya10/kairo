from workers.tasks.ingest import extract_linked_keys, process_github_webhook, process_jira_webhook


def test_extract_linked_keys():
    text = "feat(BILL-204): integrate razorpay retry, closes PAY-421"
    keys = extract_linked_keys(text)
    assert "BILL-204" in keys
    assert "PAY-421" in keys

    assert extract_linked_keys("") == []


def test_process_github_webhook_pull_request():
    payload = {
        "action": "opened",
        "repository": {"full_name": "snapmeet/billing-service"},
        "pull_request": {
            "number": 88,
            "title": "feat: razorpay retry [BILL-204]",
            "body": "Fixes BILL-204 webhook handling",
            "state": "open",
            "merged": False,
            "head": {"ref": "feat/BILL-204-retry"},
            "base": {"ref": "main"},
            "user": {"login": "rahul-snap"},
        },
    }
    result = process_github_webhook(organization_id="snapmeet", event_type="pull_request", payload=payload)
    assert result["status"] == "normalized"
    assert result["pr_number"] == 88
    assert "BILL-204" in result["linked_keys"]


def test_process_github_webhook_membership():
    payload = {
        "action": "added",
        "member": {"login": "aman-v"},
        "team": {"slug": "billing-team"},
    }
    result = process_github_webhook(organization_id="snapmeet", event_type="membership", payload=payload)
    assert result["status"] == "normalized"
    assert result["action"] == "added"
    assert result["member"] == "aman-v"


def test_process_github_webhook_unhandled():
    result = process_github_webhook(organization_id="snapmeet", event_type="star", payload={})
    assert result["status"] == "ignored_or_unhandled"


def test_process_jira_webhook_issue_updated():
    payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "BILL-204",
            "fields": {
                "summary": "Razorpay Invoicing",
                "description": "Integration task",
                "status": {"name": "In Progress"},
                "assignee": {
                    "accountId": "acc_aman",
                    "displayName": "Aman Verma",
                    "emailAddress": "aman@snapmeet.com",
                },
            },
        },
        "changelog": {
            "items": [
                {"field": "assignee", "fromString": "Rahul", "toString": "Aman"}
            ]
        },
    }
    result = process_jira_webhook(organization_id="snapmeet", event_type="jira:issue_updated", payload=payload)
    assert result["status"] == "normalized"
    assert result["external_id"] == "BILL-204"
    assert result["assignee_changed"] is True
    assert result["task_status"] == "IN_PROGRESS"


def test_process_github_webhook_closed_pr():
    payload = {
        "action": "closed",
        "repository": {"full_name": "snapmeet/billing-service"},
        "pull_request": {
            "number": 88,
            "title": "feat: razorpay retry [BILL-204]",
            "state": "closed",
            "merged": True,
            "head": {"ref": "feat/BILL-204-retry"},
            "base": {"ref": "main"},
            "user": {"login": "rahul-snap"},
        },
    }
    result = process_github_webhook(organization_id="snapmeet", event_type="pull_request", payload=payload)
    assert result["status"] == "normalized"

    payload_unmerged = {
        "action": "closed",
        "repository": {"full_name": "snapmeet/billing-service"},
        "pull_request": {
            "number": 88,
            "title": "feat: razorpay retry [BILL-204]",
            "state": "closed",
            "merged": False,
            "head": {"ref": "feat/BILL-204-retry"},
            "base": {"ref": "main"},
            "user": {"login": "rahul-snap"},
        },
    }
    result2 = process_github_webhook(organization_id="snapmeet", event_type="pull_request", payload=payload_unmerged)
    assert result2["status"] == "normalized"


def test_process_jira_webhook_statuses():
    payload_done = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "BILL-204",
            "fields": {
                "summary": "Razorpay Invoicing",
                "status": {"name": "Done"},
            },
        },
    }
    res_done = process_jira_webhook(organization_id="snapmeet", event_type="jira:issue_updated", payload=payload_done)
    assert res_done["task_status"] == "DONE"

    payload_review = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "BILL-204",
            "fields": {
                "summary": "Razorpay Invoicing",
                "status": {"name": "In Review"},
            },
        },
    }
    res_review = process_jira_webhook(organization_id="snapmeet", event_type="jira:issue_updated", payload=payload_review)
    assert res_review["task_status"] == "IN_REVIEW"


def test_process_jira_webhook_empty():
    result = process_jira_webhook(organization_id="snapmeet", event_type="jira:issue_updated", payload={})
    assert result["status"] == "skipped_no_issue"


def test_process_linear_webhook():
    from workers.tasks.ingest import process_linear_webhook

    payload = {
        "action": "create",
        "data": {
            "identifier": "ENG-104",
            "title": "Setup OAuth microservice",
            "description": "Implement JWT and refresh rotation",
            "state": {"name": "In Progress"},
            "assignee": {"id": "usr_aman", "name": "Aman", "email": "aman@snapmeet.com"},
        },
    }
    result = process_linear_webhook(organization_id="snapmeet", action="create", payload=payload)
    assert result["status"] == "normalized"
    assert result["external_id"] == "ENG-104"
    assert result["task_status"] == "IN_PROGRESS"


def test_process_gitlab_webhook():
    from workers.tasks.ingest import process_gitlab_webhook

    payload = {
        "object_kind": "merge_request",
        "project": {"path_with_namespace": "snapmeet/auth-service"},
        "object_attributes": {
            "iid": 12,
            "title": "Resolve [AUTH-101] token issue",
            "description": "Closes AUTH-101",
            "source_branch": "fix/AUTH-101-token",
            "state": "opened",
        },
    }
    result = process_gitlab_webhook(organization_id="snapmeet", event_type="merge_request", payload=payload)
    assert result["status"] == "normalized"
    assert "AUTH-101" in result["linked_keys"]

    ping_payload = {"object_kind": "push", "project": {"name": "auth-service"}}
    res_push = process_gitlab_webhook(organization_id="snapmeet", event_type="push", payload=ping_payload)
    assert res_push["status"] == "acknowledged"


def test_process_github_webhook_misc():
    res_ping = process_github_webhook(
        organization_id="snapmeet",
        event_type="ping",
        payload={"repository": {"full_name": "snapmeet/test-repo"}},
    )
    assert res_ping["status"] == "normalized"

    res_unknown = process_github_webhook(
        organization_id="snapmeet",
        event_type="workflow_run",
        payload={},
    )
    assert res_unknown["status"] == "ignored_or_unhandled"


def test_embeddings_generation_and_storage():
    from workers.tasks.embeddings import generate_768_embedding, generate_and_store_embedding

    vec = generate_768_embedding("FastAPI route handler for auth tokens")
    assert len(vec) == 768
    # Vector length should be normalized (~1.0)
    norm = sum(x * x for x in vec)
    assert 0.95 <= norm <= 1.05

    result = generate_and_store_embedding(
        organization_id="snapmeet",
        repo_id="snapmeet/auth-service",
        entity_type="commit",
        entity_id="c_89a1bc",
        content_chunk="FastAPI route handler for auth tokens",
    )
    assert result["dimensions"] == 768


def test_semantic_embedding_cosine_similarity():
    from workers.tasks.embeddings import generate_768_embedding

    text1 = "PostgreSQL database table schema query and indexing"
    text2 = "SQL relational db query storage and migration"
    text3 = "Chocolate chip cookie recipe baking with sugar and eggs"

    vec1 = generate_768_embedding(text1)
    vec2 = generate_768_embedding(text2)
    vec3 = generate_768_embedding(text3)

    assert len(vec1) == 768
    assert len(vec2) == 768
    assert len(vec3) == 768

    sim_related = sum(a * b for a, b in zip(vec1, vec2))
    sim_unrelated = sum(a * b for a, b in zip(vec1, vec3))

    assert sim_related > 0.6, f"Expected high similarity for related texts, got {sim_related}"
    assert sim_unrelated < 0.2, f"Expected low similarity for unrelated texts, got {sim_unrelated}"
    assert sim_related > sim_unrelated, f"Related similarity {sim_related} must exceed unrelated {sim_unrelated}"


def test_openai_and_gemini_embedding_providers():
    from unittest.mock import MagicMock, patch

    from workers.tasks.embeddings import (
        _embed_with_gemini,
        _embed_with_openai,
    )

    fake_openai_resp = MagicMock()
    fake_openai_resp.status_code = 200
    fake_openai_resp.json.return_value = {
        "data": [{"embedding": [0.01] * 768}]
    }

    with patch("httpx.Client.post", return_value=fake_openai_resp):
        vec = _embed_with_openai("test text", "sk-test-key")
        assert vec is not None
        assert len(vec) == 768

    fake_gemini_resp = MagicMock()
    fake_gemini_resp.status_code = 200
    fake_gemini_resp.json.return_value = {
        "embedding": {"values": [0.02] * 768}
    }

    with patch("httpx.Client.post", return_value=fake_gemini_resp):
        vec_gemini = _embed_with_gemini("test text", "gemini-test-key-long-enough")
        assert vec_gemini is not None
        assert len(vec_gemini) == 768

    # Test error handling when HTTP call fails
    with patch("httpx.Client.post", side_effect=Exception("API connection timeout")):
        assert _embed_with_openai("test", "sk-bad") is None
        assert _embed_with_gemini("test", "bad-key") is None




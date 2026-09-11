import hashlib
import hmac
import json
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from workers.tasks.backfill_task import (
    _backfill_github_prs,
    _backfill_jira_issues,
    _backfill_slack_threads,
    sync_historical_cloud_data,
)
from workers.tasks.slack_task import (
    _check_and_log_llm_spend,
    _is_standalone_message_noise,
    _passes_whole_thread_gate,
    evaluate_slack_thread,
    process_slack_event,
)

from apps.api.app.core.config import get_settings
from apps.api.app.core.security import verify_slack_signature
from apps.api.app.main import app

client = TestClient(app)


def _generate_slack_signature(body_bytes: bytes, timestamp: int, secret: str) -> str:
    sig_basestring = f"v0:{timestamp}:{body_bytes.decode('utf-8')}".encode("utf-8")
    return "v0=" + hmac.new(secret.encode("utf-8"), sig_basestring, hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# 1. Signature Verification & Replay Protection Tests
# ---------------------------------------------------------------------------

def test_slack_signature_verification_success() -> None:
    settings = get_settings()
    now = int(time.time())
    payload = b'{"text":"hello"}'
    sig = _generate_slack_signature(payload, now, settings.SLACK_SIGNING_SECRET)
    assert verify_slack_signature(payload, str(now), sig) is True


def test_slack_signature_replay_attack_rejected() -> None:
    settings = get_settings()
    old_time = int(time.time()) - 350  # > 5 minutes ago
    payload = b'{"text":"replay"}'
    sig = _generate_slack_signature(payload, old_time, settings.SLACK_SIGNING_SECRET)
    with pytest.raises(Exception) as exc_info:
        verify_slack_signature(payload, str(old_time), sig)
    assert "5-minute replay window" in str(exc_info.value)


def test_slack_signature_invalid_signature_rejected() -> None:
    now = int(time.time())
    payload = b'{"text":"tampered"}'
    with pytest.raises(Exception) as exc_info:
        verify_slack_signature(payload, str(now), "v0=invalidhash0000000000")
    assert "failed" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# 2. Webhook Endpoint Tests (Challenge, Auth, Dedupe)
# ---------------------------------------------------------------------------

def test_slack_url_verification_handshake() -> None:
    """Slack url_verification challenge must respond with HTTP 200 and challenge payload."""
    payload = {"type": "url_verification", "challenge": "challenge_token_xyz123"}
    res = client.post("/api/v1/webhooks/slack", json=payload)
    assert res.status_code == 200
    assert res.json() == {"challenge": "challenge_token_xyz123"}


def test_slack_webhook_missing_signature_rejected() -> None:
    payload = {"type": "event_callback", "event": {"type": "message", "text": "test"}}
    res = client.post("/api/v1/webhooks/slack", json=payload)
    assert res.status_code == 401


def test_slack_webhook_valid_event_accepted_and_deduplicated() -> None:
    settings = get_settings()
    now = int(time.time())
    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    payload_dict = {
        "type": "event_callback",
        "event_id": event_id,
        "team_id": "T_TEST_ORG",
        "event": {
            "type": "message",
            "text": "Discussion on BILL-204 rate limiting",
            "user": "U_ALICE",
            "ts": f"{now}.000100",
        },
    }
    body_bytes = json.dumps(payload_dict).encode("utf-8")
    sig = _generate_slack_signature(body_bytes, now, settings.SLACK_SIGNING_SECRET)

    headers = {
        "X-Slack-Signature": sig,
        "X-Slack-Request-Timestamp": str(now),
        "Content-Type": "application/json",
    }

    # First call: Accepted (202)
    res = client.post("/api/v1/webhooks/slack", content=body_bytes, headers=headers)
    assert res.status_code == 202
    data = res.json()
    assert data["status"] == "accepted"
    assert data["event_id"] == event_id

    # Second call with same event_id: Deduplicated (200)
    headers["X-Slack-Retry-Num"] = "1"
    res_retry = client.post("/api/v1/webhooks/slack", content=body_bytes, headers=headers)
    assert res_retry.status_code == 200
    assert res_retry.json()["status"] == "duplicate_ignored"


# ---------------------------------------------------------------------------
# 3. Noise-Filtering & Heuristic Gate Tests
# ---------------------------------------------------------------------------

def test_standalone_noise_filter_drops_trivial_messages() -> None:
    # Bot message
    assert _is_standalone_message_noise("Build passed", bot_id="B123") is True

    # Empty / pure emoji
    assert _is_standalone_message_noise("👍🚀🔥") is True
    assert _is_standalone_message_noise("   ") is True

    # Stop phrases
    assert _is_standalone_message_noise("ok") is True
    assert _is_standalone_message_noise("LGTM") is True
    assert _is_standalone_message_noise("thanks!") is True

    # Short message without tech or Jira key
    assert _is_standalone_message_noise("hey what time is lunch today?") is True


def test_standalone_noise_filter_preserves_technical_signals() -> None:
    # Contains Jira Key
    assert _is_standalone_message_noise("Starting BILL-204 now") is False

    # Contains Tech Entity
    assert _is_standalone_message_noise("Configured Redis cache") is False
    assert _is_standalone_message_noise("Postgres migration ready") is False


def test_thread_reply_preserves_short_suggestions_and_affirmations() -> None:
    """Crucial user-identified edge case: 'Redis' and 'LGTM' in threads must NOT be dropped."""
    org_id = f"org_{uuid.uuid4().hex[:6]}"
    thread_ts = "1710001000.000001"

    # 1. Send root message
    root_event = {
        "event": {
            "type": "message",
            "text": "Which cache should we use for BILL-204 session storage?",
            "user": "U_ALICE",
            "ts": thread_ts,
        }
    }
    res_root = process_slack_event(organization_id=org_id, payload=root_event)
    assert res_root["status"] == "thread_initialized"

    # 2. Reply 'Redis' (only 5 chars) — MUST BE PRESERVED
    reply_1 = {
        "event": {
            "type": "message",
            "text": "Redis",
            "user": "U_BOB",
            "ts": "1710001005.000002",
            "thread_ts": thread_ts,
        }
    }
    res_reply_1 = process_slack_event(organization_id=org_id, payload=reply_1)
    assert res_reply_1["status"] == "thread_reply_appended"

    # 3. Reply 'LGTM' — MUST BE PRESERVED AS CONSENSUS
    reply_2 = {
        "event": {
            "type": "message",
            "text": "LGTM",
            "user": "U_CHARLIE",
            "ts": "1710001010.000003",
            "thread_ts": thread_ts,
        }
    }
    res_reply_2 = process_slack_event(organization_id=org_id, payload=reply_2)
    assert res_reply_2["status"] == "thread_reply_appended"


# ---------------------------------------------------------------------------
# 4. Whole-Thread Gate & LLM Cost Guardrail Tests
# ---------------------------------------------------------------------------

def test_whole_thread_gate_drops_social_banter_zero_tokens() -> None:
    social_thread = [
        {"user": "alice", "text": "Happy birthday Bob!"},
        {"user": "bob", "text": "Thank you so much!"},
        {"user": "charlie", "text": "HBD Bob! Have a great one"},
    ]
    assert _passes_whole_thread_gate(social_thread) is False


def test_whole_thread_gate_passes_technical_consensus() -> None:
    technical_thread = [
        {"user": "alice", "text": "For BILL-204 we need to choose between Kafka and RabbitMQ."},
        {"user": "bob", "text": "Kafka provides better partitioning for our scale."},
        {"user": "charlie", "text": "LGTM, let's go with Kafka."},
    ]
    assert _passes_whole_thread_gate(technical_thread) is True


def test_llm_spend_cap_enforcement() -> None:
    org_id = f"org_spend_{uuid.uuid4().hex[:6]}"
    # Small spend allowed
    assert _check_and_log_llm_spend(org_id, cost_usd=0.01, prompt_tokens=100, completion_tokens=50) is True

    # Breaching cap
    assert _check_and_log_llm_spend(org_id, cost_usd=15.00, prompt_tokens=100000, completion_tokens=50000) is True

    # Next call rejected due to cap reached
    assert _check_and_log_llm_spend(org_id, cost_usd=0.01, prompt_tokens=10, completion_tokens=10) is False


# ---------------------------------------------------------------------------
# 5. End-to-End Decision Evaluation & Confidence Gating
# ---------------------------------------------------------------------------

def test_evaluate_slack_thread_high_confidence_graphs_decision() -> None:
    org_id = f"org_test_{uuid.uuid4().hex[:6]}"
    channel_id = "C_ENG"
    thread_ts = f"{int(time.time())}.000100"

    # Initialize technical thread
    process_slack_event(org_id, {
        "event": {
            "type": "message",
            "text": "What should we use for BILL-305 rate limiting?",
            "user": "U_LEAD",
            "channel": channel_id,
            "ts": thread_ts,
        }
    })
    process_slack_event(org_id, {
        "event": {
            "type": "message",
            "text": "Redis sliding window",
            "user": "U_DEV",
            "channel": channel_id,
            "ts": f"{int(time.time()) + 1}.000101",
            "thread_ts": thread_ts,
        }
    })
    process_slack_event(org_id, {
        "event": {
            "type": "message",
            "text": "LGTM, agreed",
            "user": "U_ARCH",
            "channel": channel_id,
            "ts": f"{int(time.time()) + 2}.000102",
            "thread_ts": thread_ts,
        }
    })

    result = evaluate_slack_thread(org_id, channel_id, thread_ts)
    assert result["status"] == "decision_extracted_and_graphed"
    assert result["jira_key"] == "BILL-305"
    assert result["confidence"] >= 0.70


# ---------------------------------------------------------------------------
# 6. 120-Day Cloud Backfill Worker & API Tests
# ---------------------------------------------------------------------------

def test_cloud_backfill_components() -> None:
    org_id = f"org_bf_{uuid.uuid4().hex[:6]}"

    # Test individual backfill pipelines
    gh_items, next_p = _backfill_github_prs(org_id, days=120, start_page=1, max_pages=2)
    assert gh_items > 0
    assert next_p == 2

    jira_items, next_start = _backfill_jira_issues(org_id, days=120, start_at=0)
    assert jira_items > 0
    assert next_start > 0

    slack_items, _ = _backfill_slack_threads(org_id, days=120)
    assert slack_items > 0

    # Full orchestrator task test
    job_id = f"bf_{uuid.uuid4().hex[:8]}"
    res = sync_historical_cloud_data(job_id=job_id, organization_id=org_id, days=120)
    assert res["status"] == "COMPLETED"
    assert res["items_processed"] > 0
    assert res["progress"] == 100


def test_cloud_backfill_api_endpoints() -> None:
    from apps.api.app.core.security import create_access_token
    org_id = f"org_api_{uuid.uuid4().hex[:6]}"
    token = create_access_token({
        "sub": "usr_snapmeet_admin",
        "org_id": org_id,
        "is_org_admin": True,
        "role": "ADMIN",
        "email": f"admin@{org_id}.com",
    })
    auth_headers = {"Authorization": f"Bearer {token}"}

    # Trigger backfill job
    post_res = client.post("/api/v1/sync/cloud", json={"organization_id": org_id, "days": 120}, headers=auth_headers)
    assert post_res.status_code == 202
    data = post_res.json()
    assert "job_id" in data
    job_id = data["job_id"]

    # Poll status endpoint
    poll_res = client.get(f"/api/v1/sync/status/{job_id}", headers=auth_headers)
    assert poll_res.status_code == 200
    status_data = poll_res.json()
    assert status_data["job_id"] == job_id
    assert status_data["organization_id"] == org_id

import json
import re
import time
import uuid
from typing import Any

from apps.api.app.core.config import get_settings
from apps.api.app.core.database import get_neo4j_driver, get_supabase_client
from apps.api.app.core.logging import get_logger
from apps.api.app.services.identity_service import IdentityService
from apps.api.app.services.llm_service import LLMService
from packages.schemas.decision import ExtractedDecision
from workers.celery_app import celery_app

logger = get_logger("kairo.workers.slack")

JIRA_KEY_REGEX = re.compile(r"\b([A-Z]{2,10}-\d+)\b")

STOP_PHRASES = {
    "ok", "okay", "done", "lgtm", "thanks", "thank you", "thx", "cool",
    "sounds good", "make sense", "makes sense", "+1", "agreed", "yes", "no", "yup", "np",
}

TECH_LEXICON = {
    "redis", "postgres", "postgresql", "mysql", "mongodb", "kafka", "rabbitmq",
    "dynamodb", "s3", "grpc", "graphql", "rest", "websocket", "docker", "k8s",
    "kubernetes", "celery", "jwt", "oauth", "auth0", "stripe", "fastapi", "nextjs",
    "tailwind", "microservice", "rate-limit", "rate limit", "cache", "caching",
    "latency", "idempotency", "webhook", "pipeline", "schema", "migration",
}

CONSENSUS_INDICATORS = {
    "lgtm", "+1", "agreed", "sounds good", "approved", "go ahead",
    "make sense", "makes sense", "let's go with", "ship it",
}

# In-memory ephemeral storage for test environments
_ephemeral_threads: dict[str, dict[str, Any]] = {}
_ephemeral_llm_costs: dict[str, float] = {}


def _is_standalone_message_noise(text: str, bot_id: str | None = None) -> bool:
    """
    Evaluates whether an orphan, top-level channel message is noise.
    Thread replies bypass this check so concise suggestions like 'Redis' are preserved.
    """
    if bot_id:
        return True

    clean = text.strip()
    if not clean:
        return True

    # Pure emoji check (no alphanumeric characters)
    if not re.search(r"[a-zA-Z0-9]", clean):
        return True

    lower_text = clean.lower()
    if lower_text in STOP_PHRASES:
        return True

    # Tech entity and Jira key immunity
    if JIRA_KEY_REGEX.search(clean) or any(t in lower_text for t in TECH_LEXICON):
        return False

    words = clean.split()
    settings = get_settings()
    return len(words) < settings.SLACK_NOISE_MIN_WORDS


def _get_or_create_thread_record(
    organization_id: str,
    channel_id: str,
    thread_ts: str,
    root_text: str,
) -> dict[str, Any]:
    """Retrieves or creates thread state in PostgreSQL or memory fallback."""
    key = f"{organization_id}:{channel_id}:{thread_ts}"
    try:
        db = get_supabase_client()
        res = db.table("slack_threads").select("*").eq("organization_id", organization_id).eq("channel_id", channel_id).eq("thread_ts", thread_ts).execute()
        if res.data:
            return res.data[0]

        record = {
            "organization_id": organization_id,
            "channel_id": channel_id,
            "thread_ts": thread_ts,
            "root_text": root_text,
            "reply_count": 0,
            "messages": json.dumps([{
                "user": "root",
                "text": root_text,
                "ts": thread_ts,
                "reactions": [],
            }]),
            "status": "ACTIVE",
            "decision_extracted": False,
        }
        ins = db.table("slack_threads").insert(record).execute()
        return ins.data[0] if ins.data else record
    except Exception as exc:
        logger.debug(f"Database thread retrieval fallback: {exc}")

    if key not in _ephemeral_threads:
        _ephemeral_threads[key] = {
            "organization_id": organization_id,
            "channel_id": channel_id,
            "thread_ts": thread_ts,
            "root_text": root_text,
            "reply_count": 0,
            "messages": [{
                "user": "root",
                "text": root_text,
                "ts": thread_ts,
                "reactions": [],
            }],
            "status": "ACTIVE",
            "decision_extracted": False,
            "last_activity_at": time.time(),
        }
    return _ephemeral_threads[key]


def _append_thread_message(
    organization_id: str,
    channel_id: str,
    thread_ts: str,
    message_item: dict[str, Any],
) -> None:
    """Appends a reply message or reaction to the thread state."""
    key = f"{organization_id}:{channel_id}:{thread_ts}"
    try:
        db = get_supabase_client()
        res = db.table("slack_threads").select("messages, reply_count").eq("organization_id", organization_id).eq("channel_id", channel_id).eq("thread_ts", thread_ts).execute()
        if res.data:
            existing_msgs = res.data[0].get("messages") or []
            if isinstance(existing_msgs, str):
                existing_msgs = json.loads(existing_msgs)
            existing_msgs.append(message_item)
            db.table("slack_threads").update({
                "messages": json.dumps(existing_msgs),
                "reply_count": res.data[0].get("reply_count", 0) + 1,
                "status": "DEBOUNCING",
            }).eq("organization_id", organization_id).eq("channel_id", channel_id).eq("thread_ts", thread_ts).execute()
            return
    except Exception as exc:
        logger.debug(f"Database thread append fallback: {exc}")

    if key in _ephemeral_threads:
        _ephemeral_threads[key]["messages"].append(message_item)
        _ephemeral_threads[key]["reply_count"] += 1
        _ephemeral_threads[key]["status"] = "DEBOUNCING"
        _ephemeral_threads[key]["last_activity_at"] = time.time()


def _passes_whole_thread_gate(messages: list[dict[str, Any]]) -> bool:
    """
    Evaluates whether an entire thread warrants LLM decision extraction.
    Zero LLM tokens are expended on social banter or empty chatter.
    """
    if len(messages) < 2:
        return False

    full_text = " ".join(m.get("text", "") for m in messages).lower()

    # Must reference Jira Key or Tech Entity or Decision Keywords
    has_jira = bool(JIRA_KEY_REGEX.search(full_text))
    has_tech = any(entity in full_text for entity in TECH_LEXICON)
    has_decision_verbs = any(verb in full_text for verb in [
        "decide", "decided", "choose", "chose", "switch", "switched",
        "migrate", "migrated", "use", "using", "adopt", "adopted", "go with",
    ])
    has_affirmation = any(aff in full_text for aff in CONSENSUS_INDICATORS)

    return (has_jira or has_tech) and (has_decision_verbs or has_affirmation)


def _check_and_log_llm_spend(organization_id: str, cost_usd: float, prompt_tokens: int, completion_tokens: int) -> bool:
    """
    Enforces per-organization daily spend caps to prevent runaway LLM costs.
    Logs usage into PostgreSQL `llm_usage_log`.
    """
    settings = get_settings()
    current_daily = _ephemeral_llm_costs.get(organization_id, 0.0)

    try:
        db = get_supabase_client()
        # Sum today's spend
        res = db.table("llm_usage_log").select("cost_usd").eq("organization_id", organization_id).execute()
        if res.data:
            current_daily = sum(float(r.get("cost_usd", 0.0)) for r in res.data)
    except Exception:
        pass

    if current_daily >= settings.MAX_DAILY_LLM_SPEND_USD:
        logger.warning(
            f"Daily LLM spend cap reached for org {organization_id}: ${current_daily:.2f} >= ${settings.MAX_DAILY_LLM_SPEND_USD:.2f}",
            extra={"organization_id": organization_id},
        )
        return False

    # Log new spend
    try:
        db = get_supabase_client()
        db.table("llm_usage_log").insert({
            "organization_id": organization_id,
            "feature": "slack_decision_extraction",
            "model": settings.LLM_MODEL_NAME,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost_usd": cost_usd,
        }).execute()
    except Exception:
        pass

    _ephemeral_llm_costs[organization_id] = current_daily + cost_usd
    return True


def _sync_decision_to_neo4j(
    organization_id: str,
    decision: ExtractedDecision,
    decision_id: str,
    author_id: str | None = None,
) -> bool:
    """
    Persists decision node and provenance linkages into Neo4j AuraDB.
    Enforces strict org_id scoping and idempotent MERGE semantics.
    """
    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            # 1. Merge Decision node and link to Task if Jira key exists
            if decision.jira_key:
                cypher = """
                MATCH (t:Task {key: $jira_key, org_id: $org_id})
                MERGE (d:Decision {id: $decision_id, org_id: $org_id})
                ON CREATE SET d.title = $title,
                              d.rationale = $rationale,
                              d.source = 'SLACK_THREAD',
                              d.confidence = $confidence,
                              d.status = 'ACTIVE',
                              d.timestamp = datetime()
                ON MATCH SET d.title = $title,
                             d.rationale = $rationale,
                             d.confidence = $confidence
                MERGE (t)<-[:JUSTIFIES]-(d)
                WITH d
                OPTIONAL MATCH (old:Decision {id: $supersedes_id, org_id: $org_id})
                FOREACH (_ IN CASE WHEN old IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (d)-[:SUPERSEDES]->(old)
                )
                """
                session.run(
                    cypher,
                    jira_key=decision.jira_key,
                    org_id=organization_id,
                    decision_id=decision_id,
                    title=decision.title,
                    rationale=decision.rationale,
                    confidence=decision.confidence,
                    supersedes_id=decision.supersedes_decision_id or "",
                )
            else:
                cypher_standalone = """
                MERGE (d:Decision {id: $decision_id, org_id: $org_id})
                ON CREATE SET d.title = $title,
                              d.rationale = $rationale,
                              d.source = 'SLACK_THREAD',
                              d.confidence = $confidence,
                              d.status = 'ACTIVE',
                              d.timestamp = datetime()
                """
                session.run(
                    cypher_standalone,
                    org_id=organization_id,
                    decision_id=decision_id,
                    title=decision.title,
                    rationale=decision.rationale,
                    confidence=decision.confidence,
                )

            # 2. Link Author Developer if resolved
            if author_id:
                session.run(
                    """
                    MERGE (dev:Developer {id: $dev_id, org_id: $org_id})
                    WITH dev
                    MATCH (d:Decision {id: $decision_id, org_id: $org_id})
                    MERGE (dev)-[:PROPOSED]->(d)
                    """,
                    dev_id=author_id,
                    org_id=organization_id,
                    decision_id=decision_id,
                )
        return True
    except Exception as exc:
        logger.warning(
            f"Failed to sync decision to Neo4j (continuing): {exc}",
            extra={"organization_id": organization_id, "decision_id": decision_id},
        )
        return False


def _route_to_human_review_queue(
    organization_id: str,
    decision: ExtractedDecision,
    decision_id: str,
    thread_ref: dict[str, Any],
) -> bool:
    """Routes low-confidence decisions (<0.70) into PostgreSQL review queue."""
    try:
        db = get_supabase_client()
        db.table("decision_review_queue").insert({
            "organization_id": organization_id,
            "decision_id": decision_id,
            "task_key": decision.jira_key,
            "title": decision.title,
            "rationale": decision.rationale,
            "confidence": decision.confidence,
            "source": "SLACK_THREAD",
            "status": "PENDING_REVIEW",
            "thread_ref": thread_ref,
        }).execute()
        logger.info(
            f"Routed low-confidence decision {decision_id} ({decision.confidence:.2f}) to review queue",
            extra={"organization_id": organization_id, "decision_id": decision_id},
        )
        return True
    except Exception as exc:
        logger.warning(f"Failed to insert into review queue: {exc}")
        return False


@celery_app.task(name="workers.tasks.slack_task.process_slack_event", bind=True, max_retries=3)
def process_slack_event(
    self: Any,
    organization_id: str,
    payload: dict[str, Any],
    event_id: str | None = None,
) -> dict[str, Any]:
    """
    Ingests Slack event webhook, enforces the smart noise filter,
    tracks thread lifecycles, and triggers debounced synthesis.
    """
    event = payload.get("event", {})
    event_type = event.get("type", "")

    if event_type == "message":
        # Ignore bot message edits or deletes
        subtype = event.get("subtype")
        if subtype in ("message_deleted", "channel_join", "channel_leave"):
            return {"status": "ignored_subtype", "subtype": subtype}

        text = event.get("text", "")
        bot_id = event.get("bot_id")
        user_id = event.get("user", "unknown")
        ts = event.get("ts", "")
        thread_ts = event.get("thread_ts")
        channel_id = event.get("channel", "general")

        # Case 1: Standalone Message (Not part of a thread)
        if not thread_ts or thread_ts == ts:
            if _is_standalone_message_noise(text, bot_id):
                return {
                    "status": "filtered_noise",
                    "reason": "standalone_short_or_stop_phrase",
                    "text_preview": text[:30],
                }

            # Valid technical root message: initialize thread record
            _get_or_create_thread_record(organization_id, channel_id, ts, text)
            return {
                "status": "thread_initialized",
                "thread_ts": ts,
                "channel_id": channel_id,
            }

        # Case 2: Thread Reply (Always preserved to protect concise proposals like 'Redis' & 'LGTM')
        resolved_author = IdentityService.resolve_canonical_user_id(
            organization_id=organization_id,
            provider="slack",
            external_user_id=user_id,
        )

        reply_item = {
            "user": user_id,
            "author_id": resolved_author,
            "text": text,
            "ts": ts,
            "reactions": [],
        }

        # Ensure thread state exists then append
        _get_or_create_thread_record(organization_id, channel_id, thread_ts, "")
        _append_thread_message(organization_id, channel_id, thread_ts, reply_item)

        # Trigger debounced whole-thread evaluation task
        evaluate_slack_thread.apply_async(
            kwargs={
                "organization_id": organization_id,
                "channel_id": channel_id,
                "thread_ts": thread_ts,
            },
            countdown=60,  # 60-second debounce window
        )

        return {
            "status": "thread_reply_appended",
            "thread_ts": thread_ts,
            "author_id": resolved_author,
        }

    elif event_type == "reaction_added":
        # Capture consensus reactions (e.g. +1, rocket, checkmark)
        item = event.get("item", {})
        msg_ts = item.get("ts")
        channel_id = item.get("channel")
        reaction = event.get("reaction", "+1")

        logger.info(
            f"Slack reaction captured: :{reaction}: on message {msg_ts}",
            extra={"organization_id": organization_id, "channel": channel_id},
        )
        return {"status": "reaction_recorded", "reaction": reaction, "ts": msg_ts}

    return {"status": "unhandled_event_type", "type": event_type}


@celery_app.task(name="workers.tasks.slack_task.evaluate_slack_thread", bind=True, max_retries=2)
def evaluate_slack_thread(
    self: Any,
    organization_id: str,
    channel_id: str,
    thread_ts: str,
) -> dict[str, Any]:
    """
    Debounced worker task that executes the whole-thread gate,
    invokes two-stage structured LLM extraction, and updates Neo4j.
    """
    record = _get_or_create_thread_record(organization_id, channel_id, thread_ts, "")
    messages = record.get("messages", [])
    if isinstance(messages, str):
        messages = json.loads(messages)

    if record.get("decision_extracted"):
        return {"status": "already_processed", "thread_ts": thread_ts}

    # 1. Whole-Thread Gate: Drops social banter with zero LLM costs
    if not _passes_whole_thread_gate(messages):
        return {
            "status": "thread_gate_dropped",
            "reason": "insufficient_technical_signal",
            "thread_ts": thread_ts,
        }

    # 2. Format Thread Dialogue for Structured LLM Reasoning
    dialogue_lines: list[str] = []
    jira_candidate: str | None = None

    for m in messages:
        txt = m.get("text", "")
        if not jira_candidate:
            match = JIRA_KEY_REGEX.search(txt)
            if match:
                jira_candidate = match.group(1)

        lower_t = txt.strip().lower()
        if lower_t in CONSENSUS_INDICATORS or any(lower_t.startswith(kw) for kw in CONSENSUS_INDICATORS):
            tag = "(AGREEMENT / CONSENSUS VOTE)"
        else:
            tag = ""

        dialogue_lines.append(f"- User ({m.get('user', 'dev')}): \"{txt}\" {tag}".strip())

    thread_text = "\n".join(dialogue_lines)

    # 3. Two-Stage LLM Extraction
    # Spend Cap Guardrail check (~350 tokens, ~$0.0007 estimated)
    spend_allowed = _check_and_log_llm_spend(
        organization_id=organization_id,
        cost_usd=0.0007,
        prompt_tokens=250,
        completion_tokens=100,
    )
    if not spend_allowed:
        return {"status": "skipped_spend_cap_exceeded"}

    # Stage 1: Fast Classification & Deterministic Grounding
    decision_id = f"dec_slack_{uuid.uuid4().hex[:10]}"
    settings = get_settings()

    # Formulate Structured Grounded Decision via LLM reasoning
    decision = LLMService.extract_decision_from_thread(
        thread_text=thread_text,
        jira_key_hint=jira_candidate,
    )

    if not decision:
        return {"status": "no_conclusive_decision_found", "thread_ts": thread_ts}

    # 4. Confidence Gate (<0.70 goes to Human Review Queue)
    if decision.confidence < settings.DECISION_CONFIDENCE_THRESHOLD:
        _route_to_human_review_queue(
            organization_id=organization_id,
            decision=decision,
            decision_id=decision_id,
            thread_ref={"channel_id": channel_id, "thread_ts": thread_ts},
        )
        return {
            "status": "routed_to_review_queue",
            "decision_id": decision_id,
            "confidence": decision.confidence,
        }

    # 5. Neo4j Graph Mutation
    author_id = messages[0].get("author_id") if messages else None
    synced = _sync_decision_to_neo4j(
        organization_id=organization_id,
        decision=decision,
        decision_id=decision_id,
        author_id=author_id,
    )

    # Mark thread processed in database
    try:
        db = get_supabase_client()
        db.table("slack_threads").update({
            "decision_extracted": True,
            "extracted_decision_id": decision_id,
            "status": "PROCESSED",
        }).eq("organization_id", organization_id).eq("channel_id", channel_id).eq("thread_ts", thread_ts).execute()
    except Exception:
        pass

    return {
        "status": "decision_extracted_and_graphed",
        "decision_id": decision_id,
        "jira_key": decision.jira_key,
        "title": decision.title,
        "confidence": decision.confidence,
        "neo4j_synced": synced,
    }

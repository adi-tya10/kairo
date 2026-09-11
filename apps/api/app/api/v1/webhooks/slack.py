import json
from typing import Any

from apps.api.app.core.config import get_settings
from apps.api.app.core.database import get_redis_client
from apps.api.app.core.logging import get_logger
from apps.api.app.core.security import verify_slack_signature
from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from workers.celery_app import celery_app

logger = get_logger("kairo.api.webhooks.slack")
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# In-memory deduplication set for unit tests or when Redis is unavailable
_ephemeral_event_dedupe: set[str] = set()


def _is_event_duplicate(event_id: str, redis_client: Any = "AUTO") -> bool:
    """
    Checks if a Slack event_id has already been received within the deduplication window.
    Uses Redis with a 24-hour TTL; falls back gracefully to in-memory set.
    """
    if not event_id:
        return False

    if redis_client == "AUTO":
        try:
            redis_client = get_redis_client()
        except Exception:
            redis_client = None

    if redis_client is not None and redis_client is not False:
        try:
            key = f"kairo:dedupe:slack:{event_id}"
            # SETNX with 24-hour (86400s) expiration
            was_set = redis_client.set(key, "1", nx=True, ex=86400)
            return not bool(was_set)
        except Exception as exc:
            logger.debug(f"Redis dedupe check fallback: {exc}")

    if event_id in _ephemeral_event_dedupe:
        return True
    _ephemeral_event_dedupe.add(event_id)
    return False


@router.post("/slack/{org_id}", status_code=status.HTTP_202_ACCEPTED)
@router.post("/slack", status_code=status.HTTP_202_ACCEPTED)
async def handle_slack_webhook(
    request: Request,
    org_id: str | None = None,
    x_slack_signature: str | None = Header(None, alias="X-Slack-Signature"),
    x_slack_request_timestamp: str | None = Header(None, alias="X-Slack-Request-Timestamp"),
    x_slack_retry_num: str | None = Header(None, alias="X-Slack-Retry-Num"),
    x_slack_retry_reason: str | None = Header(None, alias="X-Slack-Retry-Reason"),
) -> Response:
    """
    Inbound Slack Events API webhook controller.
    1. Handles Slack url_verification challenge synchronously (<1s).
    2. Verifies HMAC SHA-256 signature with 5-minute replay window.
    3. Enforces event_id deduplication against Slack retry loops.
    4. Offloads thread aggregation, noise filtering, and LLM extraction to Celery (<3s SLA).
    """
    raw_body = await request.body()
    settings = get_settings()

    # Parse JSON payload
    try:
        payload = json.loads(raw_body) if raw_body else {}
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed JSON payload: {exc}",
        ) from exc

    # 1. Handle Slack URL Verification Handshake
    if payload.get("type") == "url_verification":
        challenge = payload.get("challenge", "")
        logger.info("Slack url_verification challenge received and answered")
        return Response(
            content=json.dumps({"challenge": challenge}),
            media_type="application/json",
            status_code=status.HTTP_200_OK,
        )

    # 2. Enforce Mandatory Signature Verification in production and tests
    if not x_slack_signature or not x_slack_request_timestamp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing mandatory Slack signature headers (X-Slack-Signature / X-Slack-Request-Timestamp).",
        )

    try:
        verify_slack_signature(raw_body, x_slack_request_timestamp, x_slack_signature)
    except Exception as exc:
        logger.warning(f"Slack webhook signature verification rejected: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    # 3. Check feature flag
    if not settings.ENABLE_SLACK_INGESTION:
        return Response(
            content=json.dumps({"status": "disabled", "detail": "Slack ingestion is disabled"}),
            media_type="application/json",
            status_code=status.HTTP_200_OK,
        )

    # 4. Extract Event Identity & Deduplicate
    event_id = payload.get("event_id", "")
    target_org_id = org_id or payload.get("team_id") or "default_org"

    if event_id and _is_event_duplicate(event_id):
        logger.info(
            f"Deduplicated repeated Slack event {event_id} (retry #{x_slack_retry_num or 0})",
            extra={"organization_id": target_org_id, "event_id": event_id},
        )
        return Response(
            content=json.dumps({"status": "duplicate_ignored", "event_id": event_id}),
            media_type="application/json",
            status_code=status.HTTP_200_OK,
        )

    # 5. Offload to Celery Background Queue
    try:
        celery_app.send_task(
            "workers.tasks.slack_task.process_slack_event",
            kwargs={
                "organization_id": target_org_id,
                "payload": payload,
                "event_id": event_id,
            },
        )
    except (RuntimeError, ConnectionError, OSError) as exc:
        logger.warning(
            f"Celery dispatch failed for Slack event {event_id}: {exc}",
            extra={"organization_id": target_org_id},
        )

    return Response(
        content=json.dumps({
            "status": "accepted",
            "event_id": event_id,
            "organization_id": target_org_id,
        }),
        media_type="application/json",
        status_code=status.HTTP_202_ACCEPTED,
    )

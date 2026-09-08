import json
from typing import Any

from apps.api.app.core.security import verify_jira_signature
from fastapi import APIRouter, Header, HTTPException, Request, status
from workers.celery_app import celery_app

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/jira/{org_id}", status_code=status.HTTP_202_ACCEPTED)
@router.post("/jira", status_code=status.HTTP_202_ACCEPTED)
async def handle_jira_webhook(
    request: Request,
    org_id: str | None = None,
    x_atlassian_webhook_identifier: str | None = Header(None, alias="X-Atlassian-Webhook-Identifier"),
    x_hub_signature: str | None = Header(None, alias="X-Hub-Signature"),
) -> dict[str, Any]:
    """
    Ingests Jira webhooks with mandatory HMAC SHA-256 signature verification.
    """
    raw_body = await request.body()
    if not x_hub_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing mandatory X-Hub-Signature header for Jira webhook.",
        )

    try:
        verify_jira_signature(raw_body, x_hub_signature)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e

    try:
        payload = json.loads(raw_body) if raw_body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {}

    event_type = payload.get("webhookEvent", "jira:issue_updated")
    target_org_id = org_id or payload.get("organization_id", "default_org")
    delivery_id = x_atlassian_webhook_identifier or "direct"

    try:
        celery_app.send_task(
            "workers.tasks.ingest.process_jira_webhook",
            kwargs={
                "organization_id": target_org_id,
                "event_type": event_type,
                "payload": payload,
                "delivery_id": delivery_id,
            },
        )
    except Exception:
        from workers.tasks.ingest import process_jira_webhook
        process_jira_webhook.apply(args=[target_org_id, event_type, payload], kwargs={"delivery_id": delivery_id})

    return {
        "status": "accepted",
        "provider": "jira",
        "event": event_type,
        "delivery_id": delivery_id,
        "organization_id": target_org_id,
    }

import json
from typing import Any

from fastapi import APIRouter, Header, Request, status
from workers.celery_app import celery_app

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/jira/{org_id}", status_code=status.HTTP_202_ACCEPTED)
@router.post("/jira", status_code=status.HTTP_202_ACCEPTED)
async def handle_jira_webhook(
    request: Request,
    org_id: str | None = None,
    x_atlassian_webhook_identifier: str | None = Header(None, alias="X-Atlassian-Webhook-Identifier"),
) -> dict[str, Any]:
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body) if raw_body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {}

    event_type = payload.get("webhookEvent", "jira:issue_updated")
    target_org_id = org_id or payload.get("organization_id", "default_org")

    try:
        celery_app.send_task(
            "workers.tasks.ingest.process_jira_webhook",
            kwargs={
                "organization_id": target_org_id,
                "event_type": event_type,
                "payload": payload,
            },
        )
    except Exception:
        from workers.tasks.ingest import process_jira_webhook
        process_jira_webhook.apply(args=[target_org_id, event_type, payload])

    return {
        "status": "accepted",
        "provider": "jira",
        "event": event_type,
        "delivery_id": x_atlassian_webhook_identifier or "direct",
        "organization_id": target_org_id,
    }

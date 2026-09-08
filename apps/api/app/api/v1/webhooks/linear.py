import json
from typing import Any

from fastapi import APIRouter, Header, Request, status
from workers.celery_app import celery_app

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/linear/{org_id}", status_code=status.HTTP_202_ACCEPTED)
@router.post("/linear", status_code=status.HTTP_202_ACCEPTED)
async def handle_linear_webhook(
    request: Request,
    org_id: str | None = None,
    linear_event: str | None = Header("Issue", alias="Linear-Event"),
    linear_delivery: str | None = Header(None, alias="Linear-Delivery"),
) -> dict[str, Any]:
    """
    Ingests Linear Webhooks (Issues, Comments, Projects, State transitions).
    """
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body) if raw_body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {}

    target_org_id = org_id or payload.get("organization_id", "default_org")
    action = payload.get("action", "update")

    try:
        celery_app.send_task(
            "workers.tasks.ingest.process_linear_webhook",
            kwargs={
                "organization_id": target_org_id,
                "action": action,
                "payload": payload,
            },
        )
    except Exception:
        from workers.tasks.ingest import process_linear_webhook
        process_linear_webhook.apply(args=[target_org_id, action, payload])

    return {
        "status": "accepted",
        "provider": "linear",
        "event": linear_event,
        "action": action,
        "delivery_id": linear_delivery or "direct_linear",
        "organization_id": target_org_id,
    }

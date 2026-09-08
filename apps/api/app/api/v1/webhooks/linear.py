import json
from typing import Any

from apps.api.app.core.security import verify_linear_signature
from fastapi import APIRouter, Header, HTTPException, Request, status
from workers.celery_app import celery_app

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/linear/{org_id}", status_code=status.HTTP_202_ACCEPTED)
@router.post("/linear", status_code=status.HTTP_202_ACCEPTED)
async def handle_linear_webhook(
    request: Request,
    org_id: str | None = None,
    linear_event: str | None = Header("Issue", alias="Linear-Event"),
    linear_delivery: str | None = Header(None, alias="Linear-Delivery"),
    linear_signature: str | None = Header(None, alias="Linear-Signature"),
) -> dict[str, Any]:
    """
    Ingests Linear Webhooks with mandatory HMAC SHA-256 signature verification.
    """
    raw_body = await request.body()
    if not linear_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing mandatory Linear-Signature header.",
        )

    try:
        verify_linear_signature(raw_body, linear_signature)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e

    try:
        payload = json.loads(raw_body) if raw_body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {}

    target_org_id = org_id or payload.get("organization_id", "default_org")
    action = payload.get("action", "update")
    delivery_id = linear_delivery or "direct_linear"

    try:
        celery_app.send_task(
            "workers.tasks.ingest.process_linear_webhook",
            kwargs={
                "organization_id": target_org_id,
                "action": action,
                "payload": payload,
                "delivery_id": delivery_id,
            },
        )
    except Exception:
        from workers.tasks.ingest import process_linear_webhook
        process_linear_webhook.apply(args=[target_org_id, action, payload], kwargs={"delivery_id": delivery_id})

    return {
        "status": "accepted",
        "provider": "linear",
        "event": linear_event,
        "action": action,
        "delivery_id": delivery_id,
        "organization_id": target_org_id,
    }

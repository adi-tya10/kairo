import json
from typing import Any

from fastapi import APIRouter, Header, Request, status
from workers.celery_app import celery_app

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/gitlab/{org_id}", status_code=status.HTTP_202_ACCEPTED)
@router.post("/gitlab", status_code=status.HTTP_202_ACCEPTED)
async def handle_gitlab_webhook(
    request: Request,
    org_id: str | None = None,
    x_gitlab_event: str = Header("Merge Request Hook", alias="X-Gitlab-Event"),
    x_gitlab_token: str | None = Header(None, alias="X-Gitlab-Token"),
) -> dict[str, Any]:
    """
    Ingests GitLab Webhooks (Merge Requests, Pipelines, Pushes).
    """
    raw_body = await request.body()
    try:
        payload = json.loads(raw_body) if raw_body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {}

    target_org_id = org_id or payload.get("organization_id", "default_org")

    try:
        celery_app.send_task(
            "workers.tasks.ingest.process_gitlab_webhook",
            kwargs={
                "organization_id": target_org_id,
                "event_type": x_gitlab_event,
                "payload": payload,
            },
        )
    except Exception:
        from workers.tasks.ingest import process_gitlab_webhook
        process_gitlab_webhook.apply(args=[target_org_id, x_gitlab_event, payload])

    return {
        "status": "accepted",
        "provider": "gitlab",
        "event": x_gitlab_event,
        "organization_id": target_org_id,
    }

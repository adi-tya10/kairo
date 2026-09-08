import json
from typing import Any

from apps.api.app.core.errors import SignatureVerificationError
from apps.api.app.core.security import verify_gitlab_token
from fastapi import APIRouter, Header, HTTPException, Request, status
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
    Ingests GitLab Webhooks (Merge Requests, Pipelines, Pushes) with mandatory token verification.
    """
    try:
        verify_gitlab_token(x_gitlab_token)
    except SignatureVerificationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Unauthorized webhook: {exc}",
        )

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

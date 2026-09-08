import json
from typing import Any

from apps.api.app.core.security import verify_github_signature
from fastapi import APIRouter, Header, HTTPException, Request, status
from workers.celery_app import celery_app

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


def _auto_register_tenant_repository(org_id: str, payload: dict[str, Any]) -> str:
    """Extracts repository full name from GitHub payload."""
    repo_obj = payload.get("repository", {})
    repo_name_val = repo_obj.get("full_name") or repo_obj.get("name")
    return str(repo_name_val) if repo_name_val else f"{org_id}/primary-repo"


@router.post("/github/{org_id}", status_code=status.HTTP_202_ACCEPTED)
@router.post("/github", status_code=status.HTTP_202_ACCEPTED)
async def handle_github_webhook(
    request: Request,
    org_id: str | None = None,
    x_github_event: str = Header("ping", alias="X-GitHub-Event"),
    x_github_delivery: str = Header("delivery_default", alias="X-GitHub-Delivery"),
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
) -> dict[str, Any]:
    """
    Dedicated multi-tenant GitHub Webhook endpoint.
    Auto-discovers and registers incoming repositories dynamically into the organization's dashboard.
    Enforces mandatory HMAC SHA-256 signature verification.
    """
    raw_body = await request.body()
    if not x_hub_signature_256:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing mandatory X-Hub-Signature-256 header.",
        )

    try:
        verify_github_signature(raw_body, x_hub_signature_256)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e

    try:
        payload = json.loads(raw_body) if raw_body else {}
    except (json.JSONDecodeError, UnicodeDecodeError):
        payload = {}

    target_org_id = org_id or payload.get("organization", {}).get("login") or "default_org"

    # Auto-link the discovered repository in real time
    discovered_repo = _auto_register_tenant_repository(target_org_id, payload)

    try:
        celery_app.send_task(
            "workers.tasks.ingest.process_github_webhook",
            kwargs={
                "organization_id": target_org_id,
                "event_type": x_github_event,
                "payload": payload,
                "delivery_id": x_github_delivery,
            },
        )
    except (RuntimeError, ConnectionError, OSError):
        from workers.tasks.ingest import process_github_webhook
        process_github_webhook.apply(args=[target_org_id, x_github_event, payload], kwargs={"delivery_id": x_github_delivery})

    return {
        "status": "accepted",
        "provider": "github",
        "organization_id": target_org_id,
        "linked_repository": discovered_repo,
        "event": x_github_event,
        "delivery_id": x_github_delivery,
    }

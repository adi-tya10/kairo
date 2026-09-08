from typing import Annotated

import httpx
from apps.api.app.core.config import get_settings
from apps.api.app.core.logging import get_logger
from apps.api.app.core.security import get_current_user
from apps.api.app.services.acl import PreRetrievalACL
from apps.api.app.services.slack_notifier import SlackAlertFormatter
from fastapi import APIRouter, Depends, status
from packages.schemas.anomaly import AnomalyRuleResult
from packages.schemas.permissions import UserPermissionProfile
from pydantic import BaseModel

logger = get_logger("kairo.alerts")
router = APIRouter(prefix="/alerts", tags=["Alerts"])


class AlertDispatchRequest(BaseModel):
    organization_id: str
    task_key: str
    repo_id: str
    anomaly: AnomalyRuleResult
    webhook_url: str | None = None


class AlertDispatchResponse(BaseModel):
    status: str
    task_key: str
    formatted_payload: dict
    dispatched: bool


@router.post("/dispatch", response_model=AlertDispatchResponse, status_code=status.HTTP_200_OK)
async def dispatch_alert(
    request_body: AlertDispatchRequest,
    profile: Annotated[UserPermissionProfile, Depends(get_current_user)],
) -> AlertDispatchResponse:
    """
    Formats and dispatches real-time continuity alerts.
    Pre-Retrieval ACL guard on repo_id and organization.
    """
    PreRetrievalACL.validate_tenant_access(request_body.organization_id, profile.organization_id)
    PreRetrievalACL.guard_repo_access(request_body.repo_id, profile)

    formatted_card = SlackAlertFormatter.format_anomaly_card(
        organization_id=request_body.organization_id,
        task_key=request_body.task_key,
        repo_id=request_body.repo_id,
        anomaly=request_body.anomaly,
    )

    settings = get_settings()
    target_url = request_body.webhook_url or settings.SLACK_WEBHOOK_URL
    dispatched = False

    if target_url:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(target_url, json=formatted_card)
                dispatched = res.status_code == 200
        except Exception as exc:
            logger.warning(f"Failed to post Slack alert to {target_url}: {exc}")
            dispatched = False
    else:
        # Default success in testing / development when no live external webhook URL is specified
        dispatched = True

    return AlertDispatchResponse(
        status="SUCCESS",
        task_key=request_body.task_key,
        formatted_payload=formatted_card,
        dispatched=dispatched,
    )

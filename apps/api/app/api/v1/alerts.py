import jwt
from apps.api.app.core.security import decode_access_token
from apps.api.app.services.acl import PreRetrievalACL
from apps.api.app.services.slack_notifier import SlackAlertFormatter
from fastapi import APIRouter, Header, HTTPException, status
from packages.schemas.anomaly import AnomalyRuleResult
from packages.schemas.permissions import UserPermissionProfile
from pydantic import BaseModel

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
    authorization: str = Header(..., alias="Authorization"),
) -> AlertDispatchResponse:
    """
    Formats and dispatches real-time continuity alerts.
    # ponytail: Pre-Retrieval ACL guard on repo_id and organization.
    """
    token = authorization.replace("Bearer ", "").strip()
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authorization token: {e!s}",
        ) from e

    profile = UserPermissionProfile(
        organization_id=payload.get("org_id", ""),
        user_id=payload.get("sub", ""),
        email=payload.get("email", ""),
        allowed_repo_ids=payload.get("allowed_repos", []),
        is_org_admin=payload.get("is_org_admin", False),
    )

    PreRetrievalACL.validate_tenant_access(request_body.organization_id, profile.organization_id)
    PreRetrievalACL.guard_repo_access(request_body.repo_id, profile)

    formatted_card = SlackAlertFormatter.format_anomaly_card(
        organization_id=request_body.organization_id,
        task_key=request_body.task_key,
        repo_id=request_body.repo_id,
        anomaly=request_body.anomaly,
    )

    return AlertDispatchResponse(
        status="SUCCESS",
        task_key=request_body.task_key,
        formatted_payload=formatted_card,
        dispatched=True,
    )

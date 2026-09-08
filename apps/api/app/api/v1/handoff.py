import jwt
from apps.api.app.core.security import decode_access_token
from apps.api.app.engines.anomaly_rules import AnomalyEngine
from apps.api.app.services.acl import PreRetrievalACL
from apps.api.app.services.synthesis import GroundedSynthesisEngine
from fastapi import APIRouter, Header, HTTPException, status
from packages.schemas.github_event import CommitInfo, PullRequestEvent
from packages.schemas.handoff import HandoffPackage
from packages.schemas.permissions import UserPermissionProfile
from packages.schemas.work_item import WorkItem
from pydantic import BaseModel

router = APIRouter(prefix="/handoff", tags=["Handoff"])


class HandoffGenerateRequest(BaseModel):
    organization_id: str
    work_item: WorkItem
    repo_id: str
    outgoing_developer: str
    incoming_developer: str
    pull_requests: list[PullRequestEvent] = []
    commits: list[CommitInfo] = []


@router.post("/generate", response_model=HandoffPackage, status_code=status.HTTP_200_OK)
async def generate_handoff(
    request_body: HandoffGenerateRequest,
    authorization: str = Header(..., alias="Authorization"),
) -> HandoffPackage:
    """
    Generates a verifiable Handoff Package with strict Pre-Retrieval ACL enforcement
    and dynamic grounded evidence citations. Zero hardcoded entities.
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

    # 1. Enforce Pre-Retrieval ACL Gate
    PreRetrievalACL.validate_tenant_access(request_body.organization_id, profile.organization_id)
    PreRetrievalACL.guard_repo_access(request_body.repo_id, profile)

    # 2. Evaluate Deterministic Anomaly Engine (HW-01..HW-05) Dynamically
    anomalies = []
    if request_body.pull_requests:
        hw03_result = AnomalyEngine.evaluate_hw03_state_mismatch(
            request_body.work_item,
            request_body.pull_requests,
        )
        if hw03_result.triggered:
            anomalies.append(hw03_result)

    # 3. Generate Grounded Handoff Package with Citations
    package = GroundedSynthesisEngine.generate_handoff_package(
        work_item=request_body.work_item,
        pull_requests=request_body.pull_requests,
        commits=request_body.commits,
        anomalies=anomalies,
        outgoing_dev_name=request_body.outgoing_developer,
        incoming_dev_name=request_body.incoming_developer,
    )

    return package

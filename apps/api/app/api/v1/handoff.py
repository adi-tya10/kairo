from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from apps.api.app.core.database import get_supabase_client
from apps.api.app.core.logging import get_logger
from apps.api.app.core.security import get_current_user
from apps.api.app.engines.anomaly_rules import AnomalyEngine
from apps.api.app.services.acl import PreRetrievalACL
from apps.api.app.services.synthesis import GroundedSynthesisEngine
from packages.schemas.github_event import CommitInfo, PullRequestEvent
from packages.schemas.handoff import HandoffPackage
from packages.schemas.permissions import UserPermissionProfile
from packages.schemas.work_item import WorkItem

logger = get_logger("kairo.api.handoff")
router = APIRouter(prefix="/handoff", tags=["Handoff"])


class HandoffGenerateRequest(BaseModel):
    organization_id: str
    work_item: WorkItem
    repo_id: str
    outgoing_developer: str
    incoming_developer: str
    pull_requests: list[PullRequestEvent] = []
    commits: list[CommitInfo] = []
    code_imported_services: list[str] = []
    diagram_documented_services: list[str] = []


@router.post("/generate", response_model=HandoffPackage, status_code=status.HTTP_200_OK)
async def generate_handoff(
    request_body: HandoffGenerateRequest,
    current_user: UserPermissionProfile = Depends(get_current_user),
) -> HandoffPackage:
    """
    Generates a verifiable Handoff Package with strict Pre-Retrieval ACL enforcement,
    evaluates deterministic anomaly engine rules (HW-01..HW-05), and persists
    the package to PostgreSQL `handoff_packages` table for historical auditability.
    """
    # 1. Enforce Pre-Retrieval ACL Gate
    PreRetrievalACL.validate_tenant_access(request_body.organization_id, current_user.organization_id)
    PreRetrievalACL.guard_repo_access(request_body.repo_id, current_user)

    # 2. Evaluate Deterministic Anomaly Engine (HW-01..HW-05) Dynamically
    anomalies = []

    # HW-01: Shadow work detection
    if request_body.commits:
        author_commits = [
            {"sha": c.sha, "message": c.message, "author": c.author_name}
            for c in request_body.commits
        ]
        hw01_result = AnomalyEngine.evaluate_hw01_shadow_work(
            author_commits=author_commits,
            linked_ticket_keys=[request_body.work_item.external_id],
        )
        if hw01_result.triggered:
            anomalies.append(hw01_result)

    # HW-02: Stalled PR detection
    if request_body.pull_requests:
        hw02_result = AnomalyEngine.evaluate_hw02_stalled_work(
            pull_requests=request_body.pull_requests,
        )
        if hw02_result.triggered:
            anomalies.append(hw02_result)

    # HW-03: State mismatch
    if request_body.pull_requests:
        hw03_result = AnomalyEngine.evaluate_hw03_state_mismatch(
            request_body.work_item,
            request_body.pull_requests,
        )
        if hw03_result.triggered:
            anomalies.append(hw03_result)

    # HW-04: Architecture Documentation Drift
    code_services = list(request_body.code_imported_services)
    diagram_services = list(request_body.diagram_documented_services)
    if not code_services and request_body.commits:
        for c in request_body.commits:
            for f in c.files_changed:
                parts = f.replace("\\", "/").split("/")
                for p in parts:
                    clean_p = p.replace(".py", "").replace(".ts", "").replace(".js", "").lower()
                    if ("service" in clean_p or "db" in clean_p or "api" in clean_p) and clean_p not in code_services:
                        code_services.append(clean_p)

    if code_services or diagram_services:
        hw04_result = AnomalyEngine.evaluate_hw04_architecture_drift(
            code_imported_services=code_services,
            diagram_documented_services=diagram_services,
        )
        if hw04_result.triggered:
            anomalies.append(hw04_result)

    # HW-05: Orphaned Dependency detection
    try:
        db = get_supabase_client()
        perms_res = db.table("user_repo_permissions").select("repo_id, user_id").eq("organization_id", request_body.organization_id).execute()
        repo_maintainers: dict[str, list[str]] = {}
        for r in (perms_res.data or []):
            repo_maintainers.setdefault(str(r.get("repo_id", "")), []).append(str(r.get("user_id", "")))
        if repo_maintainers:
            hw05_result = AnomalyEngine.evaluate_hw05_orphaned_dependency(repo_maintainers)
            if hw05_result.triggered:
                anomalies.append(hw05_result)
    except Exception:
        pass

    # 3. Generate Grounded Handoff Package with Citations
    package = GroundedSynthesisEngine.generate_handoff_package(
        work_item=request_body.work_item,
        pull_requests=request_body.pull_requests,
        commits=request_body.commits,
        anomalies=anomalies,
        outgoing_dev_name=request_body.outgoing_developer,
        incoming_dev_name=request_body.incoming_developer,
    )

    # 4. Persist Handoff Package to PostgreSQL `handoff_packages` Table
    try:
        db = get_supabase_client()
        briefing_dict = package.briefing.model_dump()
        briefing_dict["repo_name"] = request_body.repo_id
        db.table("handoff_packages").upsert({
            "id": package.handoff_id,
            "organization_id": package.organization_id,
            "task_key": package.task_key,
            "from_user_id": package.from_user_id,
            "to_user_id": package.to_user_id,
            "briefing": briefing_dict,
            "anomalies": [a.model_dump() for a in package.anomalies],
            "evidence_manifest": [e.model_dump() for e in package.evidence_manifest],
            "status": "ACTIVE",
        }).execute()
        logger.info(
            "Persisted handoff package to PostgreSQL",
            extra={"organization_id": package.organization_id, "handoff_id": package.handoff_id},
        )
    except Exception as exc:
        logger.warning(
            f"Failed to persist handoff package to PostgreSQL (continuing): {exc}",
            extra={"organization_id": package.organization_id, "handoff_id": package.handoff_id},
        )

    return package

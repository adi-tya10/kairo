from packages.schemas.handoff import EvidenceCitation, EvidenceType
from packages.schemas.permissions import UserPermissionProfile
from packages.schemas.work_item import WorkItem, WorkItemStatus


def test_work_item_validation():
    wi = WorkItem(
        id="wi_100",
        organization_id="org_snapmeet",
        external_id="BILL-204",
        project_key="BILL",
        title="Razorpay Integration",
        status=WorkItemStatus.IN_PROGRESS,
    )
    assert wi.external_id == "BILL-204"
    assert wi.status == WorkItemStatus.IN_PROGRESS


def test_evidence_citation_validation():
    citation = EvidenceCitation(
        citation_key="[PR #88]",
        evidence_type=EvidenceType.PULL_REQUEST,
        identifier="88",
        title="feat: razorpay retry queue",
        confidence=0.96,
    )
    assert citation.citation_key == "[PR #88]"
    assert citation.confidence == 0.96


def test_user_permission_profile():
    profile = UserPermissionProfile(
        organization_id="org_snapmeet",
        user_id="usr_aman",
        email="aman.verma@snapmeet.com",
        allowed_repo_ids=["snapmeet/billing-service", "snapmeet/auth-service"],
        allowed_project_keys=["BILL", "MEET"],
    )
    assert "snapmeet/billing-service" in profile.allowed_repo_ids
    assert "snapmeet/executive-financials" not in profile.allowed_repo_ids

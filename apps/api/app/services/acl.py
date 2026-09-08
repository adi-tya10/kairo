from typing import Any

from packages.schemas.permissions import UserPermissionProfile

from apps.api.app.core.errors import AccessRestrictedError, TenantIsolationError


class PreRetrievalACL:
    """
    Pre-Retrieval Access Control List (ACL) Engine.
    Filters raw context chunks and graph traversals BEFORE LLM synthesis.
    """

    @staticmethod
    def validate_tenant_access(requested_org_id: str, current_org_id: str) -> None:
        if requested_org_id != current_org_id:
            raise TenantIsolationError(
                f"Tenant boundary violation: User org '{current_org_id}' cannot access '{requested_org_id}'"
            )

    @staticmethod
    def filter_authorized_repos(
        repo_id: str,
        user_profile: UserPermissionProfile,
    ) -> bool:
        if user_profile.is_org_admin:
            return True
        return repo_id in user_profile.allowed_repo_ids

    @staticmethod
    def guard_repo_access(
        repo_id: str,
        user_profile: UserPermissionProfile,
    ) -> None:
        if not PreRetrievalACL.filter_authorized_repos(repo_id, user_profile):
            raise AccessRestrictedError(
                f"Access Restricted: User '{user_profile.user_id}' does not have permission for repo '{repo_id}'",
                details={"user_id": user_profile.user_id, "attempted_repo": repo_id},
            )

    @staticmethod
    def filter_context_chunks(
        chunks: list[dict[str, Any]],
        user_profile: UserPermissionProfile,
    ) -> list[dict[str, Any]]:
        if user_profile.is_org_admin:
            return chunks
        allowed = set(user_profile.allowed_repo_ids)
        return [c for c in chunks if c.get("repo_id") in allowed]

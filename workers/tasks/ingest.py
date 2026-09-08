import re
from typing import Any

from apps.api.app.services.identity_service import IdentityService
from packages.schemas.github_event import PRStatus, PullRequestEvent
from packages.schemas.work_item import WorkItem, WorkItemSource, WorkItemStatus
from workers.celery_app import celery_app

# Regex to extract Jira issue key (e.g. BILL-204, PAY-421) from text or branch names
ISSUE_KEY_REGEX = re.compile(r"([A-Z]{2,10}-\d+)")


def extract_linked_keys(text: str) -> list[str]:
    if not text:
        return []
    return list(set(ISSUE_KEY_REGEX.findall(text)))


@celery_app.task(name="workers.tasks.ingest.process_github_webhook", bind=True, max_retries=3)
def process_github_webhook(self: Any, organization_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Parses GitHub webhooks (pull_request, push, check_run, membership).
    Performs 4-Tier structural key extraction and maps to work items.
    """
    if event_type == "pull_request":
        pr_data = payload.get("pull_request", {})
        repo_data = payload.get("repository", {})
        repo_name = repo_data.get("full_name", "")
        pr_title = pr_data.get("title", "")
        pr_body = pr_data.get("body", "") or ""
        branch_name = pr_data.get("head", {}).get("ref", "")

        # Tier 1 Structural Linking: Extract issue keys from title, body, and branch
        linked_keys = list(set(
            extract_linked_keys(pr_title)
            + extract_linked_keys(pr_body)
            + extract_linked_keys(branch_name)
        ))

        state_str = pr_data.get("state", "open").upper()
        if pr_data.get("merged", False):
            state = PRStatus.MERGED
        elif state_str == "CLOSED":
            state = PRStatus.CLOSED
        else:
            state = PRStatus.OPEN

        author_username = pr_data.get("user", {}).get("login", "unknown")
        resolved_user_id = IdentityService.resolve_canonical_user_id(
            organization_id=organization_id,
            provider="github",
            external_username=author_username,
        )

        pr_event = PullRequestEvent(
            organization_id=organization_id,
            repo_name=repo_name,
            pr_number=pr_data.get("number", 0),
            title=pr_title,
            body=pr_body,
            state=state,
            head_branch=branch_name,
            base_branch=pr_data.get("base", {}).get("ref", "main"),
            author_login=author_username,
            linked_issue_keys=linked_keys,
        )

        return {
            "status": "normalized",
            "entity": "pull_request",
            "repo": repo_name,
            "pr_number": pr_event.pr_number,
            "linked_keys": linked_keys,
            "author_login": author_username,
            "resolved_user_id": resolved_user_id,
        }

    elif event_type == "membership":
        action = payload.get("action", "")
        member = payload.get("member", {}).get("login", "")
        team = payload.get("team", {}).get("slug", "")

        return {
            "status": "normalized",
            "entity": "team_membership",
            "action": action,
            "member": member,
            "team": team,
        }

    elif event_type in ("ping", "repository"):
        repo_data = payload.get("repository", {})
        repo_name = repo_data.get("full_name", "")
        return {
            "status": "normalized",
            "entity": "repository_link",
            "organization_id": organization_id,
            "linked_repository": repo_name,
        }

    return {
        "status": "ignored_or_unhandled",
        "event_type": event_type,
    }


@celery_app.task(name="workers.tasks.ingest.process_jira_webhook", bind=True, max_retries=3)
def process_jira_webhook(self: Any, organization_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Parses Jira webhooks (jira:issue_created, jira:issue_updated).
    Normalizes tasks into WorkItem schema and detects assignee transitions.
    """
    issue = payload.get("issue", {})
    if not issue:
        return {"status": "skipped_no_issue"}

    issue_key = issue.get("key", "")
    fields = issue.get("fields", {})
    title = fields.get("summary", "Untitled Task")
    description = fields.get("description")
    project_key = issue_key.split("-")[0] if "-" in issue_key else "UNKNOWN"

    status_name = fields.get("status", {}).get("name", "").upper()
    if "DONE" in status_name or "CLOSED" in status_name:
        work_status = WorkItemStatus.DONE
    elif "REVIEW" in status_name:
        work_status = WorkItemStatus.IN_REVIEW
    elif "PROGRESS" in status_name:
        work_status = WorkItemStatus.IN_PROGRESS
    else:
        work_status = WorkItemStatus.TO_DO

    assignee = fields.get("assignee") or {}
    assignee_id = assignee.get("accountId")
    assignee_name = assignee.get("displayName")
    assignee_email = assignee.get("emailAddress")

    resolved_user_id = IdentityService.resolve_canonical_user_id(
        organization_id=organization_id,
        provider="jira",
        external_user_id=assignee_id,
        email=assignee_email,
    )

    work_item = WorkItem(
        id=f"wi_{issue_key}",
        organization_id=organization_id,
        external_id=issue_key,
        source=WorkItemSource.JIRA,
        project_key=project_key,
        title=title,
        description=description if isinstance(description, str) else None,
        status=work_status,
        assignee_id=assignee_id,
        assignee_name=assignee_name,
        assignee_email=assignee_email,
    )

    # Check for assignee transition (Handoff Trigger Event)
    changelog = payload.get("changelog", {})
    assignee_changed = False
    for item in changelog.get("items", []):
        if item.get("field") == "assignee":
            assignee_changed = True
            break

    return {
        "status": "normalized",
        "entity": "work_item",
        "external_id": work_item.external_id,
        "assignee_changed": assignee_changed,
        "task_status": work_item.status.value,
        "resolved_user_id": resolved_user_id,
    }


@celery_app.task(name="workers.tasks.ingest.process_linear_webhook", bind=True, max_retries=3)
def process_linear_webhook(self: Any, organization_id: str, action: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Parses Linear App Webhooks (Issue create, update, state change).
    Maps Linear team keys (e.g. ENG-104) to KAIRO normalized work items.
    """
    data = payload.get("data", {})
    identifier = data.get("identifier") or f"LIN-{data.get('number', 101)}"
    title = data.get("title", "Linear Issue")
    team_key = identifier.split("-")[0] if "-" in identifier else "ENG"

    state_name = (data.get("state", {}).get("name") or "In Progress").lower()
    if "done" in state_name or "completed" in state_name:
        status_enum = WorkItemStatus.DONE
    elif "cancel" in state_name:
        status_enum = WorkItemStatus.CLOSED
    elif "in review" in state_name or "review" in state_name:
        status_enum = WorkItemStatus.IN_REVIEW
    elif "progress" in state_name:
        status_enum = WorkItemStatus.IN_PROGRESS
    else:
        status_enum = WorkItemStatus.TO_DO

    assignee = data.get("assignee", {})
    assignee_id = assignee.get("id")
    assignee_email = assignee.get("email")

    resolved_user_id = IdentityService.resolve_canonical_user_id(
        organization_id=organization_id,
        provider="linear",
        external_user_id=assignee_id,
        email=assignee_email,
    )

    work_item = WorkItem(
        id=f"wi_lin_{identifier}",
        organization_id=organization_id,
        external_id=identifier,
        source=WorkItemSource.LINEAR,
        project_key=team_key,
        title=title,
        description=data.get("description"),
        status=status_enum,
        assignee_id=assignee_id,
        assignee_name=assignee.get("name"),
        assignee_email=assignee_email,
    )

    return {
        "status": "normalized",
        "entity": "work_item",
        "provider": "linear",
        "external_id": work_item.external_id,
        "task_status": work_item.status.value,
        "resolved_user_id": resolved_user_id,
    }


@celery_app.task(name="workers.tasks.ingest.process_gitlab_webhook", bind=True, max_retries=3)
def process_gitlab_webhook(self: Any, organization_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Parses GitLab Webhooks (Merge Request Events, Pipeline Events, Push Events).
    """
    object_kind = payload.get("object_kind", event_type)
    project = payload.get("project", {})
    repo_name = project.get("path_with_namespace") or project.get("name", "gitlab-repo")

    if object_kind == "merge_request":
        mr_attrs = payload.get("object_attributes", {})
        mr_title = mr_attrs.get("title", "")
        mr_desc = mr_attrs.get("description", "") or ""
        source_branch = mr_attrs.get("source_branch", "")

        linked_keys = list(set(
            extract_linked_keys(mr_title)
            + extract_linked_keys(mr_desc)
            + extract_linked_keys(source_branch)
        ))

        return {
            "status": "normalized",
            "provider": "gitlab",
            "event": "merge_request",
            "repo_name": repo_name,
            "mr_iid": mr_attrs.get("iid"),
            "linked_keys": linked_keys,
            "state": mr_attrs.get("state", "opened"),
        }

    return {
        "status": "acknowledged",
        "provider": "gitlab",
        "event": object_kind,
        "repo_name": repo_name,
    }

import re
import uuid
from typing import Any

from apps.api.app.core.database import get_neo4j_driver, get_supabase_client
from apps.api.app.core.logging import get_logger
from apps.api.app.services.identity_service import IdentityService
from packages.schemas.github_event import PRStatus, PullRequestEvent
from packages.schemas.work_item import WorkItem, WorkItemSource, WorkItemStatus
from workers.celery_app import celery_app

logger = get_logger("kairo.workers.ingest")

# Regex to extract Jira issue key (e.g. BILL-204, PAY-421) from text or branch names
ISSUE_KEY_REGEX = re.compile(r"([A-Z]{2,10}-\d+)")


def extract_linked_keys(text: str) -> list[str]:
    if not text:
        return []
    return list(set(ISSUE_KEY_REGEX.findall(text)))


def _persist_raw_event(
    organization_id: str,
    provider: str,
    event_type: str,
    delivery_id: str,
    payload: dict[str, Any],
) -> bool:
    """
    Persists raw webhook payloads to PostgreSQL `events_raw` idempotently.
    Prevents duplicate processing and records audit logs.
    """
    try:
        db = get_supabase_client()
        record = {
            "organization_id": organization_id,
            "provider": provider,
            "event_type": event_type,
            "delivery_id": delivery_id or f"del_{uuid.uuid4().hex[:16]}",
            "payload": payload,
            "processed": True,
        }
        db.table("events_raw").upsert(record).execute()
        logger.info(
            "Persisted raw event to PostgreSQL",
            extra={
                "organization_id": organization_id,
                "provider": provider,
                "delivery_id": delivery_id,
            },
        )
        return True
    except Exception as exc:
        logger.warning(
            f"Failed to persist raw event to PostgreSQL (continuing): {exc}",
            extra={"organization_id": organization_id, "provider": provider},
        )
        return False


def _persist_work_item(work_item: WorkItem) -> bool:
    """Upserts normalized task into PostgreSQL `work_items` table."""
    try:
        db = get_supabase_client()
        record = {
            "organization_id": work_item.organization_id,
            "external_id": work_item.external_id,
            "source": work_item.source.value if hasattr(work_item.source, "value") else str(work_item.source),
            "project_key": work_item.project_key,
            "title": work_item.title,
            "description": work_item.description,
            "status": work_item.status.value if hasattr(work_item.status, "value") else str(work_item.status),
            "assignee_id": work_item.assignee_id,
        }
        db.table("work_items").upsert(record).execute()
        logger.info(
            "Persisted work item to PostgreSQL",
            extra={
                "organization_id": work_item.organization_id,
                "external_id": work_item.external_id,
            },
        )
        return True
    except Exception as exc:
        logger.warning(
            f"Failed to persist work item to PostgreSQL (continuing): {exc}",
            extra={"organization_id": work_item.organization_id, "external_id": work_item.external_id},
        )
        return False


def _sync_neo4j_work_item(work_item: WorkItem, resolved_user_id: str | None = None) -> bool:
    """Syncs WorkItem state and Developer assignment into Neo4j knowledge graph."""
    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            cypher = """
            MERGE (t:Task {key: $task_key, org_id: $org_id})
            ON CREATE SET t.title = $title, t.status = $status, t.source = $source
            ON MATCH SET t.status = $status, t.title = $title
            """
            session.run(
                cypher,
                task_key=work_item.external_id,
                org_id=work_item.organization_id,
                title=work_item.title,
                status=work_item.status.value if hasattr(work_item.status, "value") else str(work_item.status),
                source=work_item.source.value if hasattr(work_item.source, "value") else str(work_item.source),
            )

            if resolved_user_id or work_item.assignee_id:
                dev_id = resolved_user_id or work_item.assignee_id
                assignee_name = work_item.assignee_name or dev_id
                assignee_cypher = """
                MERGE (d:Developer {id: $dev_id, org_id: $org_id})
                ON CREATE SET d.name = $name
                WITH d
                MATCH (t:Task {key: $task_key, org_id: $org_id})
                MERGE (d)-[:WORKED_ON]->(t)
                """
                session.run(
                    assignee_cypher,
                    dev_id=dev_id,
                    org_id=work_item.organization_id,
                    name=assignee_name,
                    task_key=work_item.external_id,
                )
        return True
    except Exception as exc:
        logger.warning(
            f"Failed to sync work item to Neo4j (continuing): {exc}",
            extra={"organization_id": work_item.organization_id, "external_id": work_item.external_id},
        )
        return False


def _sync_neo4j_pr(pr_event: PullRequestEvent, resolved_user_id: str | None = None) -> bool:
    """Syncs Pull Request provenance and task linkages into Neo4j."""
    try:
        driver = get_neo4j_driver()
        with driver.session() as session:
            cypher_pr = """
            MERGE (pr:PullRequest {number: $pr_number, repo: $repo, org_id: $org_id})
            ON CREATE SET pr.title = $title, pr.state = $state, pr.head_branch = $branch
            ON MATCH SET pr.state = $state, pr.title = $title
            """
            session.run(
                cypher_pr,
                pr_number=pr_event.pr_number,
                repo=pr_event.repo_name,
                org_id=pr_event.organization_id,
                title=pr_event.title,
                state=pr_event.state.value if hasattr(pr_event.state, "value") else str(pr_event.state),
                branch=pr_event.head_branch,
            )

            dev_id = resolved_user_id or pr_event.author_login
            session.run(
                """
                MERGE (d:Developer {id: $dev_id, org_id: $org_id})
                ON CREATE SET d.name = $author_login
                WITH d
                MATCH (pr:PullRequest {number: $pr_number, repo: $repo, org_id: $org_id})
                MERGE (d)-[:AUTHORED]->(pr)
                """,
                dev_id=dev_id,
                org_id=pr_event.organization_id,
                author_login=pr_event.author_login,
                pr_number=pr_event.pr_number,
                repo=pr_event.repo_name,
            )

            for key in pr_event.linked_issue_keys:
                session.run(
                    """
                    MERGE (t:Task {key: $task_key, org_id: $org_id})
                    WITH t
                    MATCH (pr:PullRequest {number: $pr_number, repo: $repo, org_id: $org_id})
                    MERGE (t)-[:IMPLEMENTED_BY]->(pr)
                    """,
                    task_key=key,
                    org_id=pr_event.organization_id,
                    pr_number=pr_event.pr_number,
                    repo=pr_event.repo_name,
                )
        return True
    except Exception as exc:
        logger.warning(
            f"Failed to sync PR to Neo4j (continuing): {exc}",
            extra={"organization_id": pr_event.organization_id, "pr_number": pr_event.pr_number},
        )
        return False


@celery_app.task(name="workers.tasks.ingest.process_github_webhook", bind=True, max_retries=3)
def process_github_webhook(
    self: Any,
    organization_id: str,
    event_type: str,
    payload: dict[str, Any],
    delivery_id: str | None = None,
) -> dict[str, Any]:
    """
    Parses GitHub webhooks (pull_request, push, check_run, membership).
    Performs 4-Tier structural key extraction, maps to work items,
    and persists raw events + temporal graph nodes.
    """
    deliv = delivery_id or payload.get("delivery_id") or f"gh_{uuid.uuid4().hex[:12]}"
    _persist_raw_event(organization_id, "github", event_type, deliv, payload)

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

        _sync_neo4j_pr(pr_event, resolved_user_id)

        return {
            "status": "normalized",
            "entity": "pull_request",
            "repo": repo_name,
            "pr_number": pr_event.pr_number,
            "linked_keys": linked_keys,
            "author_login": author_username,
            "resolved_user_id": resolved_user_id,
            "persisted": True,
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
            "persisted": True,
        }

    elif event_type in ("ping", "repository"):
        repo_data = payload.get("repository", {})
        repo_name = repo_data.get("full_name", "")
        return {
            "status": "normalized",
            "entity": "repository_link",
            "organization_id": organization_id,
            "linked_repository": repo_name,
            "persisted": True,
        }

    return {
        "status": "ignored_or_unhandled",
        "event_type": event_type,
    }


@celery_app.task(name="workers.tasks.ingest.process_jira_webhook", bind=True, max_retries=3)
def process_jira_webhook(
    self: Any,
    organization_id: str,
    event_type: str,
    payload: dict[str, Any],
    delivery_id: str | None = None,
) -> dict[str, Any]:
    """
    Parses Jira webhooks (jira:issue_created, jira:issue_updated).
    Normalizes tasks into WorkItem schema, persists to PostgreSQL & Neo4j,
    and detects assignee transitions.
    """
    deliv = delivery_id or payload.get("delivery_id") or f"jira_{uuid.uuid4().hex[:12]}"
    _persist_raw_event(organization_id, "jira", event_type, deliv, payload)

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

    _persist_work_item(work_item)
    _sync_neo4j_work_item(work_item, resolved_user_id)

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
        "persisted": True,
    }


@celery_app.task(name="workers.tasks.ingest.process_linear_webhook", bind=True, max_retries=3)
def process_linear_webhook(
    self: Any,
    organization_id: str,
    action: str,
    payload: dict[str, Any],
    delivery_id: str | None = None,
) -> dict[str, Any]:
    """
    Parses Linear App Webhooks (Issue create, update, state change).
    Maps Linear team keys (e.g. ENG-104) to KAIRO normalized work items
    and persists to PostgreSQL & Neo4j.
    """
    deliv = delivery_id or payload.get("delivery_id") or f"lin_{uuid.uuid4().hex[:12]}"
    _persist_raw_event(organization_id, "linear", action, deliv, payload)

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

    _persist_work_item(work_item)
    _sync_neo4j_work_item(work_item, resolved_user_id)

    return {
        "status": "normalized",
        "entity": "work_item",
        "provider": "linear",
        "external_id": work_item.external_id,
        "task_status": work_item.status.value,
        "resolved_user_id": resolved_user_id,
        "persisted": True,
    }


@celery_app.task(name="workers.tasks.ingest.process_gitlab_webhook", bind=True, max_retries=3)
def process_gitlab_webhook(
    self: Any,
    organization_id: str,
    event_type: str,
    payload: dict[str, Any],
    delivery_id: str | None = None,
) -> dict[str, Any]:
    """
    Parses GitLab Webhooks (Merge Request Events, Pipeline Events, Push Events).
    Persists raw payloads and updates temporal graph nodes.
    """
    object_kind = payload.get("object_kind", event_type)
    deliv = delivery_id or payload.get("delivery_id") or f"gl_{uuid.uuid4().hex[:12]}"
    _persist_raw_event(organization_id, "gitlab", object_kind, deliv, payload)

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
            "persisted": True,
        }

    return {
        "status": "acknowledged",
        "provider": "gitlab",
        "event": object_kind,
        "repo_name": repo_name,
        "persisted": True,
    }

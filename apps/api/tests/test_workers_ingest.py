from workers.tasks.ingest import extract_linked_keys, process_github_webhook, process_jira_webhook


def test_extract_linked_keys():
    text = "feat(BILL-204): integrate razorpay retry, closes PAY-421"
    keys = extract_linked_keys(text)
    assert "BILL-204" in keys
    assert "PAY-421" in keys

    assert extract_linked_keys("") == []


def test_process_github_webhook_pull_request():
    payload = {
        "action": "opened",
        "repository": {"full_name": "snapmeet/billing-service"},
        "pull_request": {
            "number": 88,
            "title": "feat: razorpay retry [BILL-204]",
            "body": "Fixes BILL-204 webhook handling",
            "state": "open",
            "merged": False,
            "head": {"ref": "feat/BILL-204-retry"},
            "base": {"ref": "main"},
            "user": {"login": "rahul-snap"},
        },
    }
    result = process_github_webhook(organization_id="snapmeet", event_type="pull_request", payload=payload)
    assert result["status"] == "normalized"
    assert result["pr_number"] == 88
    assert "BILL-204" in result["linked_keys"]


def test_process_github_webhook_membership():
    payload = {
        "action": "added",
        "member": {"login": "aman-v"},
        "team": {"slug": "billing-team"},
    }
    result = process_github_webhook(organization_id="snapmeet", event_type="membership", payload=payload)
    assert result["status"] == "normalized"
    assert result["action"] == "added"
    assert result["member"] == "aman-v"


def test_process_github_webhook_unhandled():
    result = process_github_webhook(organization_id="snapmeet", event_type="star", payload={})
    assert result["status"] == "ignored_or_unhandled"


def test_process_jira_webhook_issue_updated():
    payload = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "BILL-204",
            "fields": {
                "summary": "Razorpay Invoicing",
                "description": "Integration task",
                "status": {"name": "In Progress"},
                "assignee": {
                    "accountId": "acc_aman",
                    "displayName": "Aman Verma",
                    "emailAddress": "aman@snapmeet.com",
                },
            },
        },
        "changelog": {
            "items": [
                {"field": "assignee", "fromString": "Rahul", "toString": "Aman"}
            ]
        },
    }
    result = process_jira_webhook(organization_id="snapmeet", event_type="jira:issue_updated", payload=payload)
    assert result["status"] == "normalized"
    assert result["external_id"] == "BILL-204"
    assert result["assignee_changed"] is True
    assert result["task_status"] == "IN_PROGRESS"


def test_process_github_webhook_closed_pr():
    payload = {
        "action": "closed",
        "repository": {"full_name": "snapmeet/billing-service"},
        "pull_request": {
            "number": 88,
            "title": "feat: razorpay retry [BILL-204]",
            "state": "closed",
            "merged": True,
            "head": {"ref": "feat/BILL-204-retry"},
            "base": {"ref": "main"},
            "user": {"login": "rahul-snap"},
        },
    }
    result = process_github_webhook(organization_id="snapmeet", event_type="pull_request", payload=payload)
    assert result["status"] == "normalized"

    payload_unmerged = {
        "action": "closed",
        "repository": {"full_name": "snapmeet/billing-service"},
        "pull_request": {
            "number": 88,
            "title": "feat: razorpay retry [BILL-204]",
            "state": "closed",
            "merged": False,
            "head": {"ref": "feat/BILL-204-retry"},
            "base": {"ref": "main"},
            "user": {"login": "rahul-snap"},
        },
    }
    result2 = process_github_webhook(organization_id="snapmeet", event_type="pull_request", payload=payload_unmerged)
    assert result2["status"] == "normalized"


def test_process_jira_webhook_statuses():
    payload_done = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "BILL-204",
            "fields": {
                "summary": "Razorpay Invoicing",
                "status": {"name": "Done"},
            },
        },
    }
    res_done = process_jira_webhook(organization_id="snapmeet", event_type="jira:issue_updated", payload=payload_done)
    assert res_done["task_status"] == "DONE"

    payload_review = {
        "webhookEvent": "jira:issue_updated",
        "issue": {
            "key": "BILL-204",
            "fields": {
                "summary": "Razorpay Invoicing",
                "status": {"name": "In Review"},
            },
        },
    }
    res_review = process_jira_webhook(organization_id="snapmeet", event_type="jira:issue_updated", payload=payload_review)
    assert res_review["task_status"] == "IN_REVIEW"


def test_process_jira_webhook_empty():
    result = process_jira_webhook(organization_id="snapmeet", event_type="jira:issue_updated", payload={})
    assert result["status"] == "skipped_no_issue"

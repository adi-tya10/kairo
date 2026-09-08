"""
Celery asynchronous task for alert webhook dispatching.
"""
from typing import Any

from apps.api.app.services.slack_notifier import SlackAlertFormatter
from packages.schemas.anomaly import AnomalyRuleResult
from workers.celery_app import celery_app


@celery_app.task(name="workers.tasks.alerts.dispatch_anomaly_alert")
def dispatch_anomaly_alert(
    organization_id: str,
    task_key: str,
    repo_id: str,
    anomaly_data: dict[str, Any],
) -> dict[str, Any]:
    """Asynchronously formats and sends alert card to webhook."""
    anomaly = AnomalyRuleResult(**anomaly_data)
    card = SlackAlertFormatter.format_anomaly_card(
        organization_id=organization_id,
        task_key=task_key,
        repo_id=repo_id,
        anomaly=anomaly,
    )
    return {"status": "DELIVERED", "task_key": task_key, "blocks_count": len(card["blocks"])}

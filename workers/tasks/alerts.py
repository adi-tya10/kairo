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
    webhook_url: str | None = None,
) -> dict[str, Any]:
    """Asynchronously formats and sends alert card to webhook with bounded retries."""
    import time
    import httpx
    from apps.api.app.core.config import get_settings
    from apps.api.app.core.logging import get_logger

    logger = get_logger("kairo.workers.alerts")
    settings = get_settings()

    anomaly = AnomalyRuleResult(**anomaly_data)
    card = SlackAlertFormatter.format_anomaly_card(
        organization_id=organization_id,
        task_key=task_key,
        repo_id=repo_id,
        anomaly=anomaly,
    )

    target_url = webhook_url or settings.SLACK_WEBHOOK_URL
    dispatched = False

    if target_url:
        for attempt in range(3):
            try:
                with httpx.Client(timeout=10.0) as client:
                    resp = client.post(target_url, json=card)
                    if resp.status_code == 200:
                        dispatched = True
                        break
                    logger.warning(
                        f"Slack task webhook status {resp.status_code} on attempt {attempt + 1}/3"
                    )
            except Exception as exc:
                logger.error(
                    f"Slack task webhook POST error on attempt {attempt + 1}/3: {exc}"
                )
            if attempt < 2:
                time.sleep(0.1 * (attempt + 1))
    else:
        dispatched = True  # Development / test mode default

    return {
        "status": "DELIVERED" if dispatched else "FAILED",
        "task_key": task_key,
        "blocks_count": len(card["blocks"]),
        "dispatched": dispatched,
    }

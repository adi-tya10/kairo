"""
KAIRO Real-Time Alert Dispatcher & Slack Block Kit Formatter.
Dispatches deterministic anomaly radar warnings to configured webhooks.
"""
from typing import Any

from packages.schemas.anomaly import AnomalyRuleResult


class SlackAlertFormatter:
    """Formats AnomalyRuleResult instances into Slack Block Kit cards."""

    @staticmethod
    def format_anomaly_card(
        organization_id: str,
        task_key: str,
        repo_id: str,
        anomaly: AnomalyRuleResult,
    ) -> dict[str, Any]:
        """
        Creates a Slack Block Kit payload with actionable remediation steps.
        # ponytail: standard dictionary structure without heavy slack_sdk dependencies.
        """
        severity_emoji = "🚨" if anomaly.severity.value == "HIGH" else "⚠️"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{severity_emoji} KAIRO Work Continuity Alert: {anomaly.rule_id}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Task Key:*\n`{task_key}`"},
                    {"type": "mrkdwn", "text": f"*Repository:*\n`{repo_id}`"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n*{anomaly.severity.value}*"},
                    {"type": "mrkdwn", "text": f"*Organization:*\n`{organization_id}`"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{anomaly.summary}*\n{anomaly.description}",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"👉 *Recommended Action:* {anomaly.recommended_action}",
                    }
                ],
            },
        ]

        return {
            "text": f"[{anomaly.severity.value}] KAIRO Alert: {anomaly.rule_id} ({anomaly.summary}) on {task_key}",
            "blocks": blocks,
        }

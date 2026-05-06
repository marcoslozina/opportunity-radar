from __future__ import annotations

import logging

import httpx

from domain.ports.notification_port import NotificationPort
from domain.value_objects.alert_payload import AlertPayload

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT_SECONDS = 10


class WebhookNotificationAdapter(NotificationPort):
    async def send_briefing(self, briefing: object, niche_name: str) -> bool:  # type: ignore[override]
        # Webhook channel is not used for briefing delivery — no-op
        logger.debug("WebhookNotificationAdapter.send_briefing is a no-op")
        return False

    async def send_alert(self, payload: AlertPayload) -> bool:
        # Called when no explicit webhook_url routing is needed.
        # AlertEvaluationService uses send_alert_to() directly for routing.
        logger.debug("WebhookNotificationAdapter.send_alert called without url — no-op")
        return False

    async def send_alert_to(self, payload: AlertPayload, webhook_url: str) -> bool:
        body = {
            "alert_rule_id": payload.alert_rule_id,
            "niche_id": payload.niche_id,
            "niche_name": payload.niche_name,
            "triggered_at": payload.triggered_at.isoformat(),
            "threshold_score": payload.threshold_score,
            "top_opportunity": {
                "topic": payload.top_opportunity_topic,
                "score_total": payload.top_opportunity_score,
                "trajectory_direction": payload.top_opportunity_trajectory,
                "domain_applicability": payload.top_opportunity_domain_applicability,
                "recommended_action": payload.top_opportunity_recommended_action,
            },
        }
        try:
            async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
                response = await client.post(webhook_url, json=body)
                response.raise_for_status()
                logger.info(
                    "Webhook delivered: rule=%s status=%d",
                    payload.alert_rule_id,
                    response.status_code,
                )
                return True
        except Exception as exc:
            logger.error(
                "Webhook delivery failed: rule=%s url=%s error=%s",
                payload.alert_rule_id,
                webhook_url,
                exc,
            )
            return False

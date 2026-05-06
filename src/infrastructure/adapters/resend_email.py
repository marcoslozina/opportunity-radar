from __future__ import annotations

import logging

import httpx

from domain.ports.notification_port import NotificationPort
from domain.value_objects.alert_payload import AlertPayload

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
RESEND_FROM = "radar@resend.dev"


class ResendEmailAdapter(NotificationPort):
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    async def send_briefing(self, briefing: object, niche_name: str) -> bool:  # type: ignore[override]
        # Briefing delivery via email is not implemented in alert-system scope.
        logger.debug("ResendEmailAdapter.send_briefing not implemented")
        return False

    async def send_alert(self, payload: AlertPayload) -> bool:
        # This adapter requires an explicit target email via send_alert_to_email().
        # AlertEvaluationService routes to send_alert_to_email() directly.
        logger.debug("ResendEmailAdapter.send_alert called without target email — no-op")
        return False

    async def send_alert_to_email(self, payload: AlertPayload, email: str) -> bool:
        subject = (
            f"[Opportunity Radar] Alert: {payload.niche_name} "
            f"— score {payload.top_opportunity_score}"
        )
        html_body = self._render_alert_html(payload)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    RESEND_API_URL,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={
                        "from": RESEND_FROM,
                        "to": [email],
                        "subject": subject,
                        "html": html_body,
                    },
                )
                response.raise_for_status()
                logger.info(
                    "Alert email delivered: rule=%s to=%s",
                    payload.alert_rule_id,
                    email,
                )
                return True
        except Exception as exc:
            logger.error(
                "Alert email failed: rule=%s error=%s",
                payload.alert_rule_id,
                exc,
            )
            return False

    def _render_alert_html(self, payload: AlertPayload) -> str:
        trajectory_html = (
            f"<p><strong>Trajectory:</strong> {payload.top_opportunity_trajectory}</p>"
            if payload.top_opportunity_trajectory
            else ""
        )
        return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 24px;">
  <h2 style="color: #1a1a2e;">Opportunity Radar Alert</h2>
  <p>A high-scoring opportunity has been detected for your niche.</p>
  <table style="width: 100%; border-collapse: collapse;">
    <tr>
      <td style="padding: 8px; border: 1px solid #e0e0e0;"><strong>Niche</strong></td>
      <td style="padding: 8px; border: 1px solid #e0e0e0;">{payload.niche_name}</td>
    </tr>
    <tr>
      <td style="padding: 8px; border: 1px solid #e0e0e0;"><strong>Threshold Score</strong></td>
      <td style="padding: 8px; border: 1px solid #e0e0e0;">{payload.threshold_score}</td>
    </tr>
    <tr>
      <td style="padding: 8px; border: 1px solid #e0e0e0;"><strong>Top Opportunity</strong></td>
      <td style="padding: 8px; border: 1px solid #e0e0e0;">{payload.top_opportunity_topic}</td>
    </tr>
    <tr>
      <td style="padding: 8px; border: 1px solid #e0e0e0;"><strong>Score</strong></td>
      <td style="padding: 8px; border: 1px solid #e0e0e0;">{payload.top_opportunity_score}</td>
    </tr>
    <tr>
      <td style="padding: 8px; border: 1px solid #e0e0e0;"><strong>Domain</strong></td>
      <td style="padding: 8px; border: 1px solid #e0e0e0;">{payload.top_opportunity_domain_applicability}</td>
    </tr>
    <tr>
      <td style="padding: 8px; border: 1px solid #e0e0e0;"><strong>Recommended Action</strong></td>
      <td style="padding: 8px; border: 1px solid #e0e0e0;">{payload.top_opportunity_recommended_action}</td>
    </tr>
  </table>
  {trajectory_html}
  <p style="color: #888; font-size: 12px; margin-top: 24px;">
    Triggered at {payload.triggered_at.isoformat()} · Alert Rule ID: {payload.alert_rule_id}
  </p>
</body>
</html>
""".strip()

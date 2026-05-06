from __future__ import annotations

import logging
from datetime import datetime, timedelta

from domain.entities.alert_rule import AlertRule
from domain.entities.briefing import Briefing
from domain.entities.niche import Niche
from domain.ports.repository_ports import AlertRuleRepository, BriefingRepository
from domain.value_objects.alert_payload import AlertPayload
from domain.value_objects.score_trajectory import ScoreTrajectory
from infrastructure.adapters.resend_email import ResendEmailAdapter
from infrastructure.adapters.webhook_notification import WebhookNotificationAdapter

logger = logging.getLogger(__name__)

SUPPRESSION_WINDOW_MINUTES = 60


class AlertEvaluationService:
    def __init__(
        self,
        alert_rule_repo: AlertRuleRepository,
        briefing_repo: BriefingRepository,
        webhook_adapter: WebhookNotificationAdapter,
        email_adapter: ResendEmailAdapter,
    ) -> None:
        self._alert_rule_repo = alert_rule_repo
        self._briefing_repo = briefing_repo
        self._webhook_adapter = webhook_adapter
        self._email_adapter = email_adapter

    async def evaluate(self, briefing: Briefing, niche: Niche) -> None:
        rules = await self._alert_rule_repo.find_active_by_niche(str(niche.id))
        if not rules:
            return

        previous_briefing = await self._briefing_repo.get_previous(niche.id)
        top_opp = max(briefing.opportunities, key=lambda o: o.score.total, default=None)
        if top_opp is None:
            return

        trajectory = self._compute_trajectory(top_opp.topic, briefing, previous_briefing)

        for rule in rules:
            try:
                await self._evaluate_rule(rule, briefing, niche, trajectory)
            except Exception as exc:
                logger.error("Alert evaluation failed: rule=%s error=%s", rule.id, exc)

    async def _evaluate_rule(
        self,
        rule: AlertRule,
        briefing: Briefing,
        niche: Niche,
        trajectory: ScoreTrajectory | None,
    ) -> None:
        qualifying = [o for o in briefing.opportunities if o.score.total >= rule.threshold_score]
        if not qualifying:
            return

        if rule.last_notified_at is not None:
            elapsed = datetime.utcnow() - rule.last_notified_at
            if elapsed < timedelta(minutes=SUPPRESSION_WINDOW_MINUTES):
                logger.info("Alert suppressed (cooldown): rule=%s", rule.id)
                return

        best = max(qualifying, key=lambda o: o.score.total)
        payload = AlertPayload(
            alert_rule_id=str(rule.id),
            niche_id=str(niche.id),
            niche_name=niche.name,
            triggered_at=datetime.utcnow(),
            threshold_score=rule.threshold_score,
            top_opportunity_topic=best.topic,
            top_opportunity_score=best.score.total,
            top_opportunity_trajectory=trajectory.direction if trajectory else None,
            top_opportunity_domain_applicability=best.domain_applicability,
            top_opportunity_recommended_action=best.recommended_action,
        )

        dispatched = await self._dispatch(rule, payload)
        if dispatched:
            rule.last_notified_at = datetime.utcnow()
            await self._alert_rule_repo.save(rule)

    async def _dispatch(self, rule: AlertRule, payload: AlertPayload) -> bool:
        results: list[bool] = []

        if rule.delivery_channel in ("webhook", "both") and rule.webhook_url:
            results.append(await self._webhook_adapter.send_alert_to(payload, rule.webhook_url))

        if rule.delivery_channel in ("email", "both") and rule.email:
            results.append(await self._email_adapter.send_alert_to_email(payload, rule.email))

        # True if at least one channel was attempted and succeeded
        return bool(results) and any(results)

    def _compute_trajectory(
        self,
        topic: str,
        current: Briefing,
        previous: Briefing | None,
    ) -> ScoreTrajectory | None:
        if previous is None:
            return None
        current_opp = next(
            (o for o in current.opportunities if o.topic.lower().strip() == topic.lower().strip()),
            None,
        )
        prev_opp = next(
            (o for o in previous.opportunities if o.topic.lower().strip() == topic.lower().strip()),
            None,
        )
        if current_opp is None or prev_opp is None:
            return None
        return ScoreTrajectory.compute(
            current_total=current_opp.score.total,
            previous_total=prev_opp.score.total,
            compared_at=previous.generated_at,
        )

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from application.services.alert_evaluation_service import AlertEvaluationService
from domain.entities.alert_rule import AlertRule, AlertRuleId
from domain.entities.briefing import Briefing, BriefingId
from domain.entities.niche import Niche, NicheId
from domain.entities.opportunity import Opportunity, OpportunityId
from domain.ports.repository_ports import AlertRuleRepository, BriefingRepository
from domain.value_objects.alert_payload import AlertPayload
from domain.value_objects.opportunity_score import OpportunityScore


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeAlertRuleRepository(AlertRuleRepository):
    def __init__(self, rules: list[AlertRule] | None = None) -> None:
        self._rules: list[AlertRule] = rules or []
        self.saved: list[AlertRule] = []

    async def save(self, rule: AlertRule) -> None:
        self.saved.append(rule)

    async def find_by_id(self, rule_id: AlertRuleId) -> AlertRule | None:
        return next((r for r in self._rules if r.id == rule_id), None)

    async def find_active_by_niche(self, niche_id: str) -> list[AlertRule]:
        return [r for r in self._rules if r.niche_id == niche_id and r.active]

    async def deactivate(self, rule_id: AlertRuleId) -> None:
        for r in self._rules:
            if r.id == rule_id:
                r.active = False

    async def list_all(self, niche_id: str | None = None) -> list[AlertRule]:
        if niche_id:
            return [r for r in self._rules if r.niche_id == niche_id]
        return list(self._rules)


class FakeBriefingRepository(BriefingRepository):
    def __init__(self, previous: Briefing | None = None) -> None:
        self._previous = previous
        self.saved: list[Briefing] = []

    async def save(self, briefing: Briefing) -> None:
        self.saved.append(briefing)

    async def get_latest(self, niche_id: NicheId) -> Briefing | None:
        return None

    async def get_previous(self, niche_id: NicheId) -> Briefing | None:
        return self._previous


class FakeWebhookAdapter:
    def __init__(self, should_succeed: bool = True) -> None:
        self._should_succeed = should_succeed
        self.calls: list[tuple[AlertPayload, str]] = []

    async def send_alert_to(self, payload: AlertPayload, webhook_url: str) -> bool:
        self.calls.append((payload, webhook_url))
        return self._should_succeed


class FakeEmailAdapter:
    def __init__(self, should_succeed: bool = True) -> None:
        self._should_succeed = should_succeed
        self.calls: list[tuple[AlertPayload, str]] = []

    async def send_alert_to_email(self, payload: AlertPayload, email: str) -> bool:
        self.calls.append((payload, email))
        return self._should_succeed


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_score(total: float) -> OpportunityScore:
    return OpportunityScore(
        trend_velocity=total / 10,
        competition_gap=total / 10,
        social_signal=total / 10,
        monetization_intent=total / 10,
        frustration_level=total / 10,
        total=total,
        confidence="high",
    )


def make_opportunity(topic: str, total: float) -> Opportunity:
    return Opportunity(
        id=OpportunityId(uuid4()),
        topic=topic,
        score=make_score(total),
        recommended_action="Do something",
        domain_applicability="general",
    )


def make_briefing(niche_id: NicheId, opportunities: list[Opportunity]) -> Briefing:
    return Briefing(
        id=BriefingId(uuid4()),
        niche_id=niche_id,
        opportunities=opportunities,
        generated_at=datetime.utcnow(),
    )


def make_niche() -> Niche:
    return Niche(
        id=NicheId(uuid4()),
        name="Test Niche",
        keywords=["test"],
    )


def make_rule(
    niche_id: str,
    threshold: float,
    channel: str = "webhook",
    webhook_url: str | None = "https://example.com/hook",
    email: str | None = None,
    last_notified_at: datetime | None = None,
) -> AlertRule:
    return AlertRule(
        id=AlertRuleId(uuid4()),
        niche_id=niche_id,
        threshold_score=threshold,
        delivery_channel=channel,
        webhook_url=webhook_url,
        email=email,
        active=True,
        last_notified_at=last_notified_at,
    )


def make_service(
    rules: list[AlertRule] | None = None,
    previous_briefing: Briefing | None = None,
    webhook_ok: bool = True,
    email_ok: bool = True,
) -> tuple[AlertEvaluationService, FakeWebhookAdapter, FakeEmailAdapter, FakeAlertRuleRepository]:
    alert_repo = FakeAlertRuleRepository(rules or [])
    briefing_repo = FakeBriefingRepository(previous=previous_briefing)
    webhook = FakeWebhookAdapter(should_succeed=webhook_ok)
    email = FakeEmailAdapter(should_succeed=email_ok)
    service = AlertEvaluationService(
        alert_rule_repo=alert_repo,  # type: ignore[arg-type]
        briefing_repo=briefing_repo,  # type: ignore[arg-type]
        webhook_adapter=webhook,  # type: ignore[arg-type]
        email_adapter=email,  # type: ignore[arg-type]
    )
    return service, webhook, email, alert_repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_evaluate_fires_when_score_above_threshold() -> None:
    niche = make_niche()
    rule = make_rule(niche_id=str(niche.id), threshold=75.0)
    briefing = make_briefing(niche.id, [make_opportunity("AI Tools", 82.5)])

    service, webhook, _, alert_repo = make_service(rules=[rule])
    await service.evaluate(briefing, niche)

    assert len(webhook.calls) == 1
    payload, url = webhook.calls[0]
    assert payload.top_opportunity_score == 82.5
    assert payload.niche_name == "Test Niche"
    assert url == "https://example.com/hook"
    assert len(alert_repo.saved) == 1


async def test_evaluate_does_not_fire_when_all_scores_below_threshold() -> None:
    niche = make_niche()
    rule = make_rule(niche_id=str(niche.id), threshold=90.0)
    briefing = make_briefing(niche.id, [make_opportunity("AI Tools", 85.0)])

    service, webhook, _, alert_repo = make_service(rules=[rule])
    await service.evaluate(briefing, niche)

    assert len(webhook.calls) == 0
    assert len(alert_repo.saved) == 0


async def test_evaluate_suppresses_when_last_notified_within_1h() -> None:
    niche = make_niche()
    recent_time = datetime.utcnow() - timedelta(minutes=30)
    rule = make_rule(niche_id=str(niche.id), threshold=70.0, last_notified_at=recent_time)
    briefing = make_briefing(niche.id, [make_opportunity("AI Tools", 88.0)])

    service, webhook, _, alert_repo = make_service(rules=[rule])
    await service.evaluate(briefing, niche)

    assert len(webhook.calls) == 0
    assert len(alert_repo.saved) == 0


async def test_evaluate_fires_when_suppression_window_expired() -> None:
    niche = make_niche()
    old_time = datetime.utcnow() - timedelta(minutes=90)
    rule = make_rule(niche_id=str(niche.id), threshold=70.0, last_notified_at=old_time)
    briefing = make_briefing(niche.id, [make_opportunity("AI Tools", 88.0)])

    service, webhook, _, alert_repo = make_service(rules=[rule])
    await service.evaluate(briefing, niche)

    assert len(webhook.calls) == 1
    assert len(alert_repo.saved) == 1


async def test_evaluate_skips_inactive_rules() -> None:
    niche = make_niche()
    rule = make_rule(niche_id=str(niche.id), threshold=70.0)
    rule.active = False
    briefing = make_briefing(niche.id, [make_opportunity("AI Tools", 88.0)])

    service, webhook, _, alert_repo = make_service(rules=[rule])
    await service.evaluate(briefing, niche)

    assert len(webhook.calls) == 0


async def test_evaluate_continues_when_one_rule_dispatch_fails() -> None:
    niche = make_niche()
    rule_fail = make_rule(niche_id=str(niche.id), threshold=70.0, webhook_url="https://bad.invalid/hook")
    rule_ok = make_rule(niche_id=str(niche.id), threshold=70.0, webhook_url="https://example.com/hook")
    briefing = make_briefing(niche.id, [make_opportunity("AI Tools", 88.0)])

    service, webhook, _, alert_repo = make_service(rules=[rule_fail, rule_ok], webhook_ok=False)
    # Even though webhook_ok=False, the service should still save (or not crash)
    # The dispatch returns False, so last_notified_at is NOT updated
    await service.evaluate(briefing, niche)

    # Two calls attempted (one per rule), none saved because webhook failed
    assert len(webhook.calls) == 2
    assert len(alert_repo.saved) == 0


async def test_evaluate_sends_null_trajectory_when_no_previous_briefing() -> None:
    niche = make_niche()
    rule = make_rule(niche_id=str(niche.id), threshold=70.0)
    briefing = make_briefing(niche.id, [make_opportunity("AI Tools", 88.0)])

    service, webhook, _, _ = make_service(rules=[rule], previous_briefing=None)
    await service.evaluate(briefing, niche)

    assert len(webhook.calls) == 1
    payload, _ = webhook.calls[0]
    assert payload.top_opportunity_trajectory is None


async def test_evaluate_computes_growing_trajectory() -> None:
    niche = make_niche()
    rule = make_rule(niche_id=str(niche.id), threshold=70.0)

    prev_briefing = make_briefing(niche.id, [make_opportunity("AI Tools", 70.0)])
    curr_briefing = make_briefing(niche.id, [make_opportunity("AI Tools", 85.0)])

    service, webhook, _, _ = make_service(rules=[rule], previous_briefing=prev_briefing)
    await service.evaluate(curr_briefing, niche)

    assert len(webhook.calls) == 1
    payload, _ = webhook.calls[0]
    assert payload.top_opportunity_trajectory == "GROWING ↑"


async def test_dispatch_sends_both_webhook_and_email_for_both_channel() -> None:
    niche = make_niche()
    rule = make_rule(
        niche_id=str(niche.id),
        threshold=70.0,
        channel="both",
        webhook_url="https://example.com/hook",
        email="user@example.com",
    )
    briefing = make_briefing(niche.id, [make_opportunity("AI Tools", 88.0)])

    service, webhook, email_adapter, _ = make_service(rules=[rule])
    await service.evaluate(briefing, niche)

    assert len(webhook.calls) == 1
    assert len(email_adapter.calls) == 1


async def test_dispatch_only_webhook_when_channel_is_webhook() -> None:
    niche = make_niche()
    rule = make_rule(
        niche_id=str(niche.id),
        threshold=70.0,
        channel="webhook",
        webhook_url="https://example.com/hook",
        email=None,
    )
    briefing = make_briefing(niche.id, [make_opportunity("AI Tools", 88.0)])

    service, webhook, email_adapter, _ = make_service(rules=[rule])
    await service.evaluate(briefing, niche)

    assert len(webhook.calls) == 1
    assert len(email_adapter.calls) == 0


async def test_evaluate_no_rules_returns_early() -> None:
    niche = make_niche()
    briefing = make_briefing(niche.id, [make_opportunity("AI Tools", 88.0)])

    service, webhook, email_adapter, _ = make_service(rules=[])
    await service.evaluate(briefing, niche)

    assert len(webhook.calls) == 0
    assert len(email_adapter.calls) == 0


async def test_evaluate_empty_briefing_returns_early() -> None:
    niche = make_niche()
    rule = make_rule(niche_id=str(niche.id), threshold=70.0)
    briefing = make_briefing(niche.id, [])  # no opportunities

    service, webhook, email_adapter, _ = make_service(rules=[rule])
    await service.evaluate(briefing, niche)

    assert len(webhook.calls) == 0
    assert len(email_adapter.calls) == 0

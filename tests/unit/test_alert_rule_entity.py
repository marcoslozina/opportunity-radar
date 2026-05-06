from __future__ import annotations

from uuid import UUID

import pytest

from domain.entities.alert_rule import AlertRule, AlertRuleId


def test_create_alert_rule_produces_correct_defaults() -> None:
    rule = AlertRule.create(
        niche_id="niche-123",
        threshold_score=75.0,
        delivery_channel="webhook",
        webhook_url="https://example.com/hook",
    )

    assert isinstance(rule.id, AlertRuleId)
    assert isinstance(rule.id.value, UUID)
    assert rule.niche_id == "niche-123"
    assert rule.threshold_score == 75.0
    assert rule.delivery_channel == "webhook"
    assert rule.webhook_url == "https://example.com/hook"
    assert rule.email is None
    assert rule.active is True
    assert rule.last_notified_at is None
    assert rule.created_at is not None


def test_create_alert_rule_with_email_channel() -> None:
    rule = AlertRule.create(
        niche_id="niche-456",
        threshold_score=50.0,
        delivery_channel="email",
        email="user@example.com",
    )

    assert rule.delivery_channel == "email"
    assert rule.email == "user@example.com"
    assert rule.webhook_url is None


def test_create_alert_rule_with_both_channel() -> None:
    rule = AlertRule.create(
        niche_id="niche-789",
        threshold_score=80.0,
        delivery_channel="both",
        webhook_url="https://example.com/hook",
        email="user@example.com",
    )

    assert rule.delivery_channel == "both"
    assert rule.webhook_url == "https://example.com/hook"
    assert rule.email == "user@example.com"


def test_alert_rule_id_str_returns_uuid_string() -> None:
    rule = AlertRule.create(
        niche_id="niche-123",
        threshold_score=60.0,
        delivery_channel="webhook",
        webhook_url="https://example.com/hook",
    )
    rule_id_str = str(rule.id)
    # Should be a valid UUID string
    parsed = UUID(rule_id_str)
    assert parsed == rule.id.value


def test_create_alert_rule_generates_unique_ids() -> None:
    rule_a = AlertRule.create(
        niche_id="niche-1",
        threshold_score=70.0,
        delivery_channel="webhook",
        webhook_url="https://example.com/a",
    )
    rule_b = AlertRule.create(
        niche_id="niche-1",
        threshold_score=70.0,
        delivery_channel="webhook",
        webhook_url="https://example.com/b",
    )

    assert rule_a.id != rule_b.id


def test_alert_rule_active_can_be_mutated() -> None:
    rule = AlertRule.create(
        niche_id="niche-1",
        threshold_score=50.0,
        delivery_channel="webhook",
        webhook_url="https://example.com/hook",
    )
    assert rule.active is True
    rule.active = False
    assert rule.active is False

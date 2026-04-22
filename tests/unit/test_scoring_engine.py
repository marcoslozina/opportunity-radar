from __future__ import annotations

from datetime import datetime, timezone

from application.services.scoring_engine import ScoringEngine
from domain.value_objects.trend_signal import TrendSignal

_NOW = datetime.now(tz=timezone.utc)


def _signal(source: str, topic: str, raw: float, stype: str) -> TrendSignal:
    return TrendSignal(source=source, topic=topic, raw_value=raw, signal_type=stype, collected_at=_NOW)


def test_score_when_three_sources_then_confidence_is_medium() -> None:
    engine = ScoringEngine()
    signals = [
        _signal("google_trends", "angular signals", 0.8, "trend_velocity"),
        _signal("reddit", "angular signals", 0.6, "social_signal"),
        _signal("serp", "angular signals", 0.7, "competition_gap"),
    ]
    scores = engine.score(signals)
    assert "angular signals" in scores
    assert scores["angular signals"].confidence == "medium"


def test_score_when_four_sources_then_confidence_is_high() -> None:
    engine = ScoringEngine()
    signals = [
        _signal("google_trends", "angular signals", 0.8, "trend_velocity"),
        _signal("reddit", "angular signals", 0.6, "social_signal"),
        _signal("serp", "angular signals", 0.7, "competition_gap"),
        _signal("product_hunt", "angular signals", 0.9, "monetization_intent"),
    ]
    scores = engine.score(signals)
    assert scores["angular signals"].confidence == "high"


def test_score_when_one_source_then_confidence_is_low() -> None:
    engine = ScoringEngine()
    signals = [_signal("google_trends", "react", 0.5, "trend_velocity")]
    scores = engine.score(signals)
    assert scores["react"].confidence == "low"


def test_score_total_is_within_0_100() -> None:
    engine = ScoringEngine()
    signals = [
        _signal("google_trends", "topic", 1.0, "trend_velocity"),
        _signal("reddit", "topic", 1.0, "social_signal"),
        _signal("serp", "topic", 1.0, "competition_gap"),
        _signal("product_hunt", "topic", 1.0, "monetization_intent"),
    ]
    scores = engine.score(signals)
    assert 0 <= scores["topic"].total <= 100


def test_score_groups_signals_by_topic() -> None:
    engine = ScoringEngine()
    signals = [
        _signal("google_trends", "topic-a", 0.5, "trend_velocity"),
        _signal("google_trends", "topic-b", 0.8, "trend_velocity"),
    ]
    scores = engine.score(signals)
    assert "topic-a" in scores
    assert "topic-b" in scores
    assert len(scores) == 2

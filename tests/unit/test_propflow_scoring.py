from __future__ import annotations

from datetime import datetime, timezone
from application.services.scoring_engine import RealEstateScoringEngine
from domain.value_objects.trend_signal import TrendSignal

_NOW = datetime.now(tz=timezone.utc)


def _signal(stype: str, raw: float) -> TrendSignal:
    return TrendSignal(
        source="test", topic="immobilier", raw_value=raw, signal_type=stype, collected_at=_NOW
    )


def test_real_estate_scoring_weights_correctly() -> None:
    engine = RealEstateScoringEngine()
    # social 0.15, trend 0.15, competition 0.20, monetization 0.30, frustration 0.20
    # total = (0.15*6 + 0.15*8 + 0.20*7 + 0.30*9 + 0.20*5) * 10
    # total = (0.9 + 1.2 + 1.4 + 2.7 + 1.0) * 10 = 7.2 * 10 = 72
    signals = [
        _signal("social_signal", 0.6),
        _signal("trend_velocity", 0.8),
        _signal("competition_gap", 0.7),
        _signal("monetization_intent", 0.9),
        _signal("frustration_level", 0.5),
    ]
    scores = engine.score(signals)
    score = scores["immobilier"]
    
    assert score.total == 72.0
    assert score.social_signal == 6.0
    assert score.trend_velocity == 8.0
    assert score.competition_gap == 7.0
    assert score.monetization_intent == 9.0
    assert score.frustration_level == 5.0

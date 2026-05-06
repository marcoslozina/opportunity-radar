from __future__ import annotations

from datetime import datetime
import pytest
from application.services.scoring_engine import ESGScoringEngine
from domain.value_objects.trend_signal import TrendSignal


def test_esg_scoring_engine_weights():
    engine = ESGScoringEngine()
    # Weights: social 0.10, trend 0.15, competition 0.30, monetization 0.20, frustration 0.25
    assert engine.weights["social_signal"] == 0.10
    assert engine.weights["trend_velocity"] == 0.15
    assert engine.weights["competition_gap"] == 0.30
    assert engine.weights["monetization_intent"] == 0.20
    assert engine.weights["frustration_level"] == 0.25


def test_esg_scoring_high_frustration_and_gap():
    engine = ESGScoringEngine()
    # 0.25 weight for frustration + 0.30 for gap = 0.55 total weight for these two
    now = datetime.now()
    signals = [
        TrendSignal(source="reddit", topic="ESG Repo", raw_value=0.9, signal_type="frustration_level", collected_at=now),
        TrendSignal(source="reddit", topic="ESG Repo", raw_value=0.8, signal_type="competition_gap", collected_at=now),
        TrendSignal(source="youtube", topic="ESG Repo", raw_value=0.5, signal_type="social_signal", collected_at=now),
        TrendSignal(source="youtube", topic="ESG Repo", raw_value=0.5, signal_type="trend_velocity", collected_at=now),
        TrendSignal(source="reddit", topic="ESG Repo", raw_value=0.5, signal_type="monetization_intent", collected_at=now),
    ]
    
    # 0.9 * 0.25 * 10 = 2.25
    # 0.8 * 0.30 * 10 = 2.40
    # 0.5 * 0.10 * 10 = 0.50
    # 0.5 * 0.15 * 10 = 0.75
    # 0.5 * 0.20 * 10 = 1.00
    # Total weighted sum * 10 (since raw_value is 0-1 and we want 0-10)
    # Wait, the engine does: dims[k] = avg(values) * 10
    # So dims: frust=9.0, gap=8.0, social=5.0, trend=5.0, monet=5.0
    # total = sum(dims[k] * weight[k]) * 10 ? 
    # Let's check scoring_engine.py again.
    # total = sum(dims[k] * self.weights.get(k, 0.0) for k in dims) * 10
    # wait, if dims are already 0-10, then dims * weight is 0-10, sum is 0-10.
    # * 10 makes it 0-100. YES.
    
    scores = engine.score(signals)
    esg_score = scores["ESG Repo"]
    
    assert esg_score.frustration_level == 9.0
    assert esg_score.competition_gap == 8.0
    # (9*0.25 + 8*0.30 + 5*0.10 + 5*0.15 + 5*0.20) * 10
    # (2.25 + 2.40 + 0.50 + 0.75 + 1.00) * 10 = 6.9 * 10 = 69.0
    assert esg_score.total == 69.0
    assert esg_score.confidence == "medium"  # 2 sources

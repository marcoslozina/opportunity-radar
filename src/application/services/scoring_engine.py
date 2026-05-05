from __future__ import annotations

from collections import defaultdict

from domain.value_objects.opportunity_score import OpportunityScore
from domain.value_objects.trend_signal import TrendSignal


class ScoringEngine:
    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = weights or {
            "trend_velocity": 0.30,
            "competition_gap": 0.25,
            "social_signal": 0.20,
            "monetization_intent": 0.25,
            "frustration_level": 0.0,
        }

    def score(self, signals: list[TrendSignal]) -> dict[str, OpportunityScore]:
        by_topic: dict[str, list[TrendSignal]] = defaultdict(list)
        for signal in signals:
            by_topic[signal.topic].append(signal)

        return {
            topic: self._score_topic(topic_signals)
            for topic, topic_signals in by_topic.items()
        }

    def _score_topic(self, signals: list[TrendSignal]) -> OpportunityScore:
        by_type: dict[str, list[float]] = defaultdict(list)
        for signal in signals:
            by_type[signal.signal_type].append(signal.raw_value)

        sources_count = len({s.source for s in signals})

        def avg(values: list[float]) -> float:
            return (sum(values) / len(values) * 10) if values else 0.0

        # Calculate dimensions
        dims = {
            "trend_velocity": avg(by_type["trend_velocity"]),
            "competition_gap": avg(by_type["competition_gap"]),
            "social_signal": avg(by_type["social_signal"]),
            "monetization_intent": avg(by_type["monetization_intent"]),
            "frustration_level": avg(by_type["frustration_level"]),
        }

        # Calculate total weighted score
        total = sum(dims[k] * self.weights.get(k, 0.0) for k in dims) * 10

        # Determine confidence
        if sources_count >= 4:
            confidence = "high"
        elif sources_count >= 2:
            confidence = "medium"
        else:
            confidence = "low"

        return OpportunityScore(
            trend_velocity=round(dims["trend_velocity"], 2),
            competition_gap=round(dims["competition_gap"], 2),
            social_signal=round(dims["social_signal"], 2),
            monetization_intent=round(dims["monetization_intent"], 2),
            frustration_level=round(dims["frustration_level"], 2),
            total=round(total, 2),
            confidence=confidence,
        )


class PropFlowScoringEngine(ScoringEngine):
    def __init__(self) -> None:
        super().__init__(
            weights={
                "social_signal": 0.15,
                "trend_velocity": 0.15,
                "competition_gap": 0.20,
                "monetization_intent": 0.30,
                "frustration_level": 0.20,
            }
        )


class ScoringFactory:
    @staticmethod
    def get_engine(discovery_mode: str) -> ScoringEngine:
        if discovery_mode == "real_estate":
            return PropFlowScoringEngine()
        return ScoringEngine()

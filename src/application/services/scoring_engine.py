from __future__ import annotations

from collections import defaultdict

from domain.value_objects.opportunity_score import OpportunityScore
from domain.value_objects.trend_signal import TrendSignal


class ScoringEngine:
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

        return OpportunityScore.from_dimensions(
            trend_velocity=avg(by_type["trend_velocity"]),
            competition_gap=avg(by_type["competition_gap"]),
            social_signal=avg(by_type["social_signal"]),
            monetization_intent=avg(by_type["monetization_intent"]),
            sources_count=sources_count,
        )

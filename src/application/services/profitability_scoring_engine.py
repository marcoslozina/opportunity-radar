from __future__ import annotations

import logging
from collections import defaultdict

from domain.value_objects.profitability_score import ProfitabilityScore
from domain.value_objects.trend_signal import TrendSignal

logger = logging.getLogger(__name__)

_SIGNAL_TYPE_TO_DIM: dict[str, str] = {
    "frustration_level": "frustration_level",
    "market_size": "market_size",
    "competition_gap": "competition_gap",
    "monetization_intent": "willingness_to_pay",
}


class ProfitabilityScoringEngine:
    def score(self, signals: list[TrendSignal]) -> list[tuple[str, ProfitabilityScore]]:
        by_topic: dict[str, list[TrendSignal]] = defaultdict(list)
        for signal in signals:
            by_topic[signal.topic].append(signal)

        return [
            (topic, self._score_topic(topic_signals))
            for topic, topic_signals in by_topic.items()
        ]

    def _score_topic(self, signals: list[TrendSignal]) -> ProfitabilityScore:
        by_dim: dict[str, list[float]] = defaultdict(list)

        for signal in signals:
            dim = _SIGNAL_TYPE_TO_DIM.get(signal.signal_type)
            if dim is not None:
                by_dim[dim].append(signal.raw_value)
            else:
                logger.warning("Unknown signal_type '%s' — ignored", signal.signal_type)

        def avg_scaled(values: list[float]) -> float:
            return (sum(values) / len(values) * 10) if values else 0.0

        return ProfitabilityScore.from_dimensions(
            frustration_level=avg_scaled(by_dim["frustration_level"]),
            market_size=avg_scaled(by_dim["market_size"]),
            competition_gap=avg_scaled(by_dim["competition_gap"]),
            willingness_to_pay=avg_scaled(by_dim["willingness_to_pay"]),
        )

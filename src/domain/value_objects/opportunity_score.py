from __future__ import annotations

from dataclasses import dataclass

WEIGHTS = {
    "trend_velocity": 0.30,
    "competition_gap": 0.25,
    "social_signal": 0.20,
    "monetization_intent": 0.25,
}


@dataclass(frozen=True)
class OpportunityScore:
    trend_velocity: float       # 0–10
    competition_gap: float      # 0–10
    social_signal: float        # 0–10
    monetization_intent: float  # 0–10
    total: float                # 0–100
    confidence: str             # "high" | "medium" | "low"

    @classmethod
    def from_dimensions(
        cls,
        trend_velocity: float,
        competition_gap: float,
        social_signal: float,
        monetization_intent: float,
        sources_count: int,
    ) -> OpportunityScore:
        total = (
            trend_velocity * WEIGHTS["trend_velocity"]
            + competition_gap * WEIGHTS["competition_gap"]
            + social_signal * WEIGHTS["social_signal"]
            + monetization_intent * WEIGHTS["monetization_intent"]
        ) * 10  # escala 0–10 → 0–100

        if sources_count >= 4:
            confidence = "high"
        elif sources_count >= 2:
            confidence = "medium"
        else:
            confidence = "low"

        return cls(
            trend_velocity=round(trend_velocity, 2),
            competition_gap=round(competition_gap, 2),
            social_signal=round(social_signal, 2),
            monetization_intent=round(monetization_intent, 2),
            total=round(total, 2),
            confidence=confidence,
        )

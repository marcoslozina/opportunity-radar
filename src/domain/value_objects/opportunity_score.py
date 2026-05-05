from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class OpportunityScore:
    trend_velocity: float       # 0–10
    competition_gap: float      # 0–10
    social_signal: float        # 0–10
    monetization_intent: float  # 0–10
    frustration_level: float    # 0–10
    total: float                # 0–100
    confidence: str             # "high" | "medium" | "low"


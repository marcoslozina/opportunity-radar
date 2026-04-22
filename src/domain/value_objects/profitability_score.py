from __future__ import annotations

from dataclasses import dataclass

WEIGHTS = {
    "frustration_level": 0.30,
    "market_size": 0.25,
    "competition_gap": 0.25,
    "willingness_to_pay": 0.20,
}


@dataclass(frozen=True)
class ProfitabilityScore:
    frustration_level: float    # 0–10
    market_size: float          # 0–10
    competition_gap: float      # 0–10
    willingness_to_pay: float   # 0–10
    total: float                # 0–100
    confidence: str             # "high" | "medium" | "low"

    @classmethod
    def from_dimensions(
        cls,
        frustration_level: float,
        market_size: float,
        competition_gap: float,
        willingness_to_pay: float,
    ) -> ProfitabilityScore:
        total = (
            frustration_level * WEIGHTS["frustration_level"]
            + market_size * WEIGHTS["market_size"]
            + competition_gap * WEIGHTS["competition_gap"]
            + willingness_to_pay * WEIGHTS["willingness_to_pay"]
        ) * 10  # escala 0–10 → 0–100

        dims = [frustration_level, market_size, competition_gap, willingness_to_pay]
        active_dims = sum(1 for d in dims if d > 0)

        if active_dims >= 4:
            confidence = "high"
        elif active_dims >= 2:
            confidence = "medium"
        else:
            confidence = "low"

        return cls(
            frustration_level=round(frustration_level, 2),
            market_size=round(market_size, 2),
            competition_gap=round(competition_gap, 2),
            willingness_to_pay=round(willingness_to_pay, 2),
            total=round(total, 2),
            confidence=confidence,
        )

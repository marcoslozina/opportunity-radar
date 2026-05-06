from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ScoreTrajectory:
    previous_total: float
    delta: float
    delta_pct: float
    direction: str
    compared_at: datetime

    @classmethod
    def compute(
        cls,
        current_total: float,
        previous_total: float,
        compared_at: datetime,
    ) -> ScoreTrajectory:
        delta = round(current_total - previous_total, 2)
        delta_pct = round((delta / previous_total) * 100, 2) if previous_total != 0 else 0.0
        if delta_pct >= 5.0:
            direction = "GROWING ↑"
        elif delta_pct <= -5.0:
            direction = "COOLING ↓"
        else:
            direction = "STABLE →"
        return cls(
            previous_total=previous_total,
            delta=delta,
            delta_pct=delta_pct,
            direction=direction,
            compared_at=compared_at,
        )

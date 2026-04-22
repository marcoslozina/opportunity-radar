from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

SIGNAL_TYPES = frozenset(
    {"trend_velocity", "competition_gap", "social_signal", "monetization_intent"}
)


@dataclass(frozen=True)
class TrendSignal:
    source: str
    topic: str
    raw_value: float  # 0.0–1.0 normalizado por el adapter
    signal_type: str  # one of SIGNAL_TYPES
    collected_at: datetime

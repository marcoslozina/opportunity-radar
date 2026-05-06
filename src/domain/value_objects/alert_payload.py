from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AlertPayload:
    alert_rule_id: str
    niche_id: str
    niche_name: str
    triggered_at: datetime
    threshold_score: float
    top_opportunity_topic: str
    top_opportunity_score: float
    top_opportunity_trajectory: str | None   # "GROWING ↑" | "COOLING ↓" | "STABLE →" | None
    top_opportunity_domain_applicability: str
    top_opportunity_recommended_action: str

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass(frozen=True)
class AlertRuleId:
    value: UUID

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class AlertRule:
    id: AlertRuleId
    niche_id: str                      # UUID as str — consistent with existing pattern
    threshold_score: float             # 0.0–100.0; fires when any opportunity >= this
    delivery_channel: str              # "webhook" | "email" | "both"
    webhook_url: str | None
    email: str | None
    active: bool = field(default=True)
    last_notified_at: datetime | None = field(default=None)
    created_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(
        cls,
        niche_id: str,
        threshold_score: float,
        delivery_channel: str,
        webhook_url: str | None = None,
        email: str | None = None,
    ) -> AlertRule:
        return cls(
            id=AlertRuleId(uuid4()),
            niche_id=niche_id,
            threshold_score=threshold_score,
            delivery_channel=delivery_channel,
            webhook_url=webhook_url,
            email=email,
        )

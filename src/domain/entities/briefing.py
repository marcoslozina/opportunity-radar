from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from domain.entities.niche import NicheId
from domain.entities.opportunity import Opportunity


@dataclass(frozen=True)
class BriefingId:
    value: UUID

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class Briefing:
    id: BriefingId
    niche_id: NicheId
    opportunities: list[Opportunity]
    generated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def create(cls, niche_id: NicheId, opportunities: list[Opportunity]) -> Briefing:
        return cls(id=BriefingId(uuid4()), niche_id=niche_id, opportunities=opportunities)

    @property
    def top_10(self) -> list[Opportunity]:
        return sorted(self.opportunities, key=lambda o: o.score.total, reverse=True)[:10]

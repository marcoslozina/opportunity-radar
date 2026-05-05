from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from domain.value_objects.opportunity_score import OpportunityScore


@dataclass(frozen=True)
class OpportunityId:
    value: UUID

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class Opportunity:
    id: OpportunityId
    topic: str
    score: OpportunityScore
    recommended_action: str = field(default="")
    domain_applicability: str = field(default="")
    domain_reasoning: str = field(default="")

    @classmethod
    def create(cls, topic: str, score: OpportunityScore) -> Opportunity:
        return cls(id=OpportunityId(uuid4()), topic=topic, score=score)

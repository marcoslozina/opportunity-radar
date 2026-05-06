from __future__ import annotations

from domain.entities.briefing import Briefing
from domain.entities.niche import NicheId
from domain.entities.opportunity import Opportunity
from domain.value_objects.opportunity_score import OpportunityScore
from uuid import uuid4


def _opportunity(topic: str, total: float) -> Opportunity:
    score = OpportunityScore(
        trend_velocity=5.0,
        competition_gap=5.0,
        social_signal=5.0,
        monetization_intent=5.0,
        frustration_level=5.0,
        total=total,
        confidence="medium",
    )
    return Opportunity.create(topic=topic, score=score)


def test_top_10_when_more_than_10_returns_top_sorted() -> None:
    niche_id = NicheId(uuid4())
    opportunities = [_opportunity(f"topic-{i}", float(i)) for i in range(15)]
    briefing = Briefing.create(niche_id=niche_id, opportunities=opportunities)

    top = briefing.top_10
    assert len(top) == 10
    assert top[0].score.total == 14.0
    assert top[-1].score.total == 5.0


def test_top_10_when_less_than_10_returns_all() -> None:
    niche_id = NicheId(uuid4())
    opportunities = [_opportunity(f"topic-{i}", float(i)) for i in range(6)]
    briefing = Briefing.create(niche_id=niche_id, opportunities=opportunities)

    assert len(briefing.top_10) == 6


def test_top_10_is_sorted_descending() -> None:
    niche_id = NicheId(uuid4())
    opportunities = [_opportunity("a", 30.0), _opportunity("b", 90.0), _opportunity("c", 60.0)]
    briefing = Briefing.create(niche_id=niche_id, opportunities=opportunities)

    scores = [o.score.total for o in briefing.top_10]
    assert scores == sorted(scores, reverse=True)

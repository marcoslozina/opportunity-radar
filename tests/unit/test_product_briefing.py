from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from domain.entities.product_briefing import ProductBriefing
from domain.entities.product_opportunity import ProductOpportunity
from domain.value_objects.profitability_score import ProfitabilityScore

_NOW = datetime.now(tz=timezone.utc)


def _opportunity(topic: str, total: float) -> ProductOpportunity:
    score = ProfitabilityScore.from_dimensions(
        frustration_level=total / 10,
        market_size=total / 10,
        competition_gap=0.0,
        willingness_to_pay=0.0,
    )
    # Override total to the exact value we want for predictable ordering
    score = ProfitabilityScore(
        frustration_level=score.frustration_level,
        market_size=score.market_size,
        competition_gap=0.0,
        willingness_to_pay=0.0,
        total=total,
        confidence=score.confidence,
    )
    return ProductOpportunity(
        id=str(uuid4()),
        niche_id=str(uuid4()),
        topic=topic,
        score=score,
        product_type=None,
        product_reasoning="",
        recommended_price_range="",
        created_at=_NOW,
    )


def test_top_5_returns_top_5_sorted() -> None:
    opportunities = [_opportunity(f"topic-{i}", float(i * 10)) for i in range(8)]
    briefing = ProductBriefing(
        id=str(uuid4()),
        niche_id=str(uuid4()),
        opportunities=opportunities,
        generated_at=_NOW,
    )

    top = briefing.top_5
    assert len(top) == 5
    assert top[0].score.total == 70.0
    assert top[-1].score.total == 30.0


def test_top_5_returns_all_if_less_than_5() -> None:
    opportunities = [_opportunity(f"topic-{i}", float(i * 10)) for i in range(3)]
    briefing = ProductBriefing(
        id=str(uuid4()),
        niche_id=str(uuid4()),
        opportunities=opportunities,
        generated_at=_NOW,
    )

    assert len(briefing.top_5) == 3


def test_top_5_empty_list() -> None:
    briefing = ProductBriefing(
        id=str(uuid4()),
        niche_id=str(uuid4()),
        opportunities=[],
        generated_at=_NOW,
    )

    assert briefing.top_5 == []

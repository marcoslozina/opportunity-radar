from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.entities.product_briefing import ProductBriefing
from domain.entities.product_opportunity import ProductOpportunity
from domain.ports.product_repository_ports import (
    ProductBriefingRepository,
    ProductOpportunityRepository,
)
from domain.value_objects.product_type import ProductType
from domain.value_objects.profitability_score import ProfitabilityScore
from infrastructure.db.models import ProductBriefingModel, ProductOpportunityModel


class SQLProductOpportunityRepository(ProductOpportunityRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, opportunity: ProductOpportunity) -> None:
        existing = await self._session.get(ProductOpportunityModel, opportunity.id)
        if existing:
            existing.niche_id = opportunity.niche_id
            existing.topic = opportunity.topic
            existing.frustration_level = opportunity.score.frustration_level
            existing.market_size = opportunity.score.market_size
            existing.competition_gap = opportunity.score.competition_gap
            existing.willingness_to_pay = opportunity.score.willingness_to_pay
            existing.total = opportunity.score.total
            existing.confidence = opportunity.score.confidence
            existing.product_type = opportunity.product_type.value if opportunity.product_type else None
            existing.product_reasoning = opportunity.product_reasoning
            existing.recommended_price_range = opportunity.recommended_price_range
        else:
            model = _opportunity_to_model(opportunity)
            self._session.add(model)
        await self._session.commit()

    async def get_by_niche(self, niche_id: str) -> list[ProductOpportunity]:
        stmt = (
            select(ProductOpportunityModel)
            .where(ProductOpportunityModel.niche_id == niche_id)
            .order_by(ProductOpportunityModel.created_at.desc())
        )
        rows = await self._session.scalars(stmt)
        return [_opportunity_to_entity(row) for row in rows]


class SQLProductBriefingRepository(ProductBriefingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, briefing: ProductBriefing) -> None:
        model = ProductBriefingModel(
            id=briefing.id,
            niche_id=briefing.niche_id,
            generated_at=briefing.generated_at,
        )
        for opp in briefing.opportunities:
            opp_model = _opportunity_to_model(opp)
            opp_model.briefing_id = briefing.id
            model.opportunities.append(opp_model)
        self._session.add(model)
        await self._session.commit()

    async def get_latest(self, niche_id: str) -> ProductBriefing | None:
        stmt = (
            select(ProductBriefingModel)
            .options(selectinload(ProductBriefingModel.opportunities))
            .where(ProductBriefingModel.niche_id == niche_id)
            .order_by(ProductBriefingModel.generated_at.desc())
            .limit(1)
        )
        result = await self._session.scalar(stmt)
        return _briefing_to_entity(result) if result else None


# --- mappers ---

def _opportunity_to_model(opportunity: ProductOpportunity) -> ProductOpportunityModel:
    return ProductOpportunityModel(
        id=opportunity.id,
        niche_id=opportunity.niche_id,
        topic=opportunity.topic,
        frustration_level=opportunity.score.frustration_level,
        market_size=opportunity.score.market_size,
        competition_gap=opportunity.score.competition_gap,
        willingness_to_pay=opportunity.score.willingness_to_pay,
        total=opportunity.score.total,
        confidence=opportunity.score.confidence,
        product_type=opportunity.product_type.value if opportunity.product_type else None,
        product_reasoning=opportunity.product_reasoning,
        recommended_price_range=opportunity.recommended_price_range,
        created_at=opportunity.created_at,
    )


def _opportunity_to_entity(model: ProductOpportunityModel) -> ProductOpportunity:
    score = ProfitabilityScore(
        frustration_level=model.frustration_level or 0.0,
        market_size=model.market_size or 0.0,
        competition_gap=model.competition_gap or 0.0,
        willingness_to_pay=model.willingness_to_pay or 0.0,
        total=model.total or 0.0,
        confidence=model.confidence or "low",
    )
    product_type: ProductType | None = None
    if model.product_type:
        try:
            product_type = ProductType(model.product_type)
        except ValueError:
            product_type = None
    return ProductOpportunity(
        id=model.id,
        niche_id=model.niche_id,
        topic=model.topic,
        score=score,
        product_type=product_type,
        product_reasoning=model.product_reasoning or "",
        recommended_price_range=model.recommended_price_range or "",
        created_at=model.created_at,
    )


def _briefing_to_entity(model: ProductBriefingModel) -> ProductBriefing:
    return ProductBriefing(
        id=model.id,
        niche_id=model.niche_id,
        opportunities=[_opportunity_to_entity(o) for o in model.opportunities],
        generated_at=model.generated_at,
    )

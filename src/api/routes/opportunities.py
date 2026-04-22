from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.opportunity import OpportunityResponse, OpportunityScoreResponse
from domain.entities.niche import NicheId
from infrastructure.db.repositories import SQLOpportunityRepository
from infrastructure.db.session import get_session

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("", response_model=list[OpportunityResponse])
async def list_opportunities(
    niche_id: str = Query(...),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    session: AsyncSession = Depends(get_session),
) -> list[OpportunityResponse]:
    repo = SQLOpportunityRepository(session)
    cursor_uuid = UUID(cursor) if cursor else None
    opportunities = await repo.find_by_niche(
        NicheId(UUID(niche_id)), cursor=cursor_uuid, limit=limit
    )
    return [
        OpportunityResponse(
            id=str(o.id),
            topic=o.topic,
            score=OpportunityScoreResponse(
                trend_velocity=o.score.trend_velocity,
                competition_gap=o.score.competition_gap,
                social_signal=o.score.social_signal,
                monetization_intent=o.score.monetization_intent,
                total=o.score.total,
                confidence=o.score.confidence,
            ),
            recommended_action=o.recommended_action,
        )
        for o in opportunities
    ]

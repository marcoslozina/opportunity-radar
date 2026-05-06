from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.api_key import get_api_key
from api.middleware.limiter import limiter
from api.middleware.rate_limits import get_rate_limit
from api.schemas.opportunity import OpportunityResponse, OpportunityScoreResponse
from domain.entities.niche import NicheId
from domain.value_objects.api_key_context import ApiKeyContext
from infrastructure.db.repositories import SQLOpportunityRepository
from infrastructure.db.session import get_session

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.get("", response_model=list[OpportunityResponse])
@limiter.limit(get_rate_limit)
async def list_opportunities(
    request: Request,
    niche_id: str = Query(...),
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, le=100),
    session: AsyncSession = Depends(get_session),
    api_key_ctx: ApiKeyContext = Depends(get_api_key),
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

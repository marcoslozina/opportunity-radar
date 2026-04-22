from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.opportunity import BriefingResponse, OpportunityResponse, OpportunityScoreResponse
from application.use_cases.get_briefing import GetBriefingUseCase
from domain.entities.niche import NicheId
from infrastructure.db.repositories import SQLBriefingRepository
from infrastructure.db.session import get_session

router = APIRouter(prefix="/briefing", tags=["briefing"])


@router.get("/{niche_id}", response_model=BriefingResponse)
async def get_briefing(
    niche_id: str,
    session: AsyncSession = Depends(get_session),
) -> BriefingResponse:
    repo = SQLBriefingRepository(session)
    use_case = GetBriefingUseCase(repo)
    briefing = await use_case.execute(NicheId(UUID(niche_id)))

    if briefing is None:
        raise HTTPException(status_code=404, detail="No briefing found for this niche")

    return BriefingResponse(
        id=str(briefing.id),
        niche_id=str(briefing.niche_id),
        generated_at=briefing.generated_at.isoformat(),
        opportunities=[
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
            for o in briefing.top_10
        ],
    )

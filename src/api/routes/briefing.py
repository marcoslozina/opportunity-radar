from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.api_key import get_api_key
from api.middleware.limiter import limiter
from api.middleware.rate_limits import get_rate_limit
from api.schemas.opportunity import (
    BriefingResponse,
    DimensionsResponse,
    EvidenceItemResponse,
    OpportunityDNAResponse,
    OpportunityResponse,
    OpportunityScoreResponse,
    ScoreTrajectoryResponse,
)
from application.services.trajectory_service import TrajectoryService
from domain.value_objects.opportunity_dna import OpportunityDNA
from domain.value_objects.opportunity_score import OpportunityScore
from application.use_cases.get_briefing import GetBriefingUseCase
from domain.entities.niche import NicheId
from domain.value_objects.api_key_context import ApiKeyContext
from domain.value_objects.score_trajectory import ScoreTrajectory
from infrastructure.db.repositories import SQLBriefingRepository
from infrastructure.db.session import get_session

router = APIRouter(prefix="/briefing", tags=["briefing"])

_trajectory_service = TrajectoryService()


def _to_dna_response(score: OpportunityScore) -> OpportunityDNAResponse:
    dna = OpportunityDNA.from_score(score)
    return OpportunityDNAResponse(
        archetype=dna.archetype,
        archetype_description=dna.archetype_description,
        dimensions=DimensionsResponse(**dna.dimensions),
        dominant_signal=dna.dominant_signal,
    )


def _to_trajectory_response(
    t: ScoreTrajectory | None,
) -> ScoreTrajectoryResponse | None:
    if t is None:
        return None
    return ScoreTrajectoryResponse(
        previous_total=t.previous_total,
        delta=t.delta,
        delta_pct=t.delta_pct,
        direction=t.direction,
        compared_at=t.compared_at,
    )


@router.get("/{niche_id}", response_model=BriefingResponse)
@limiter.limit(get_rate_limit)
async def get_briefing(
    request: Request,
    niche_id: str,
    session: AsyncSession = Depends(get_session),
    api_key_ctx: ApiKeyContext = Depends(get_api_key),
) -> BriefingResponse:
    repo = SQLBriefingRepository(session)
    use_case = GetBriefingUseCase(repo=repo, trajectory_service=_trajectory_service)
    result = await use_case.execute(NicheId(UUID(niche_id)))

    if result is None:
        raise HTTPException(status_code=404, detail="No briefing found for this niche")

    briefing, trajectory_map = result

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
                trajectory=_to_trajectory_response(
                    trajectory_map.get(o.topic.lower().strip())
                ),
                dna=_to_dna_response(o.score),
                evidence=[
                    EvidenceItemResponse(
                        source=e.source,
                        signal_type=e.signal_type,
                        topic=e.topic,
                        title=e.title,
                        url=e.url,
                        engagement_count=e.engagement_count,
                        engagement_label=e.engagement_label,
                        collected_at=e.collected_at.isoformat(),
                    )
                    for e in o.evidence
                ],
            )
            for o in briefing.top_10
        ],
    )

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.api_key import get_api_key
from api.middleware.limiter import limiter
from api.middleware.rate_limits import get_rate_limit
from api.schemas.product_opportunity import (
    ProductBriefingResponse,
    ProductOpportunityResponse,
    ProfitabilityScoreResponse,
)
from application.use_cases.get_product_briefing import (
    GetProductBriefingUseCase,
    ProductBriefingNotFoundError,
)
from domain.value_objects.api_key_context import ApiKeyContext
from infrastructure.db.product_repositories import SQLProductBriefingRepository
from infrastructure.db.session import get_session

router = APIRouter(prefix="/product-briefing", tags=["product-briefing"])


@router.get("/{niche_id}", response_model=ProductBriefingResponse)
@limiter.limit(get_rate_limit)
async def get_product_briefing(
    request: Request,
    niche_id: str,
    session: AsyncSession = Depends(get_session),
    api_key_ctx: ApiKeyContext = Depends(get_api_key),
) -> ProductBriefingResponse:
    repo = SQLProductBriefingRepository(session)
    use_case = GetProductBriefingUseCase(repo)

    try:
        briefing = await use_case.execute(niche_id)
    except ProductBriefingNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"No product briefing found for niche '{niche_id}'",
        )

    return ProductBriefingResponse(
        id=briefing.id,
        niche_id=briefing.niche_id,
        generated_at=briefing.generated_at,
        opportunities=[
            ProductOpportunityResponse(
                id=o.id,
                topic=o.topic,
                score=ProfitabilityScoreResponse(
                    frustration_level=o.score.frustration_level,
                    market_size=o.score.market_size,
                    competition_gap=o.score.competition_gap,
                    willingness_to_pay=o.score.willingness_to_pay,
                    total=o.score.total,
                    confidence=o.score.confidence,
                ),
                product_type=o.product_type.value if o.product_type else None,
                product_reasoning=o.product_reasoning,
                recommended_price_range=o.recommended_price_range,
                created_at=o.created_at,
            )
            for o in briefing.top_5
        ],
    )

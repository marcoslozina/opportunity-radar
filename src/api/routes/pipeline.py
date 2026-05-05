from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.niche import NicheId
from infrastructure.db.repositories import SQLNicheRepository
from infrastructure.db.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


class RunPipelineRequest(BaseModel):
    mode: str = "both"


class RunPipelineResponse(BaseModel):
    status: str
    niche_id: str
    mode: str


async def _run_content_pipeline(niche_id_str: str) -> None:
    try:
        from config import settings
        from infrastructure.db.session import AsyncSessionFactory
        from infrastructure.db.repositories import SQLNicheRepository, SQLBriefingRepository
        from infrastructure.adapters.hacker_news import HackerNewsAdapter
        from infrastructure.adapters.reddit import RedditAdapter
        from infrastructure.adapters.google_trends import GoogleTrendsAdapter
        from infrastructure.adapters.youtube import YouTubeAdapter
        from infrastructure.adapters.product_hunt import ProductHuntAdapter
        from infrastructure.adapters.serp import SerpAdapter
        from infrastructure.adapters.claude_insight import ClaudeInsightAdapter
        from application.services.scoring_engine import ScoringEngine
        from application.use_cases.run_pipeline import RunPipelineUseCase

        async with AsyncSessionFactory() as session:
            use_case = RunPipelineUseCase(
                niche_repo=SQLNicheRepository(session),
                briefing_repo=SQLBriefingRepository(session),
                collectors=[
                    HackerNewsAdapter(),
                    RedditAdapter(),
                    GoogleTrendsAdapter(),
                    YouTubeAdapter(),
                    ProductHuntAdapter(),
                    SerpAdapter(),
                ],
                insight_port=ClaudeInsightAdapter(),
            )
            await use_case.execute(NicheId(UUID(niche_id_str)))
            logger.info("Manual content pipeline completed for niche_id=%s", niche_id_str)
    except Exception as exc:
        logger.error("Manual content pipeline failed for niche_id=%s: %s", niche_id_str, exc)


async def _run_product_pipeline(niche_id_str: str) -> None:
    try:
        from infrastructure.db.session import AsyncSessionFactory
        from infrastructure.db.repositories import SQLNicheRepository
        from infrastructure.db.product_repositories import SQLProductBriefingRepository
        from infrastructure.adapters.frustration_signal import RedditFrustrationAdapter, HNFrustrationAdapter
        from infrastructure.adapters.serp_product import SerpProductAdapter
        from infrastructure.adapters.serp import SerpAdapter
        from infrastructure.adapters.claude_product_discovery import ClaudeProductDiscoveryAdapter
        from application.services.profitability_scoring_engine import ProfitabilityScoringEngine
        from application.use_cases.run_product_discovery import RunProductDiscoveryUseCase
        from config import settings

        async with AsyncSessionFactory() as session:
            use_case = RunProductDiscoveryUseCase(
                niche_repo=SQLNicheRepository(session),
                product_briefing_repo=SQLProductBriefingRepository(session),
                collectors=[
                    HNFrustrationAdapter(),
                    RedditFrustrationAdapter(settings),
                    SerpProductAdapter(settings),
                    SerpAdapter(),
                ],
                discovery_port=ClaudeProductDiscoveryAdapter(settings),
                scoring_engine=ProfitabilityScoringEngine(),
            )
            await use_case.execute(NicheId(UUID(niche_id_str)))
            logger.info("Manual product pipeline completed for niche_id=%s", niche_id_str)
    except Exception as exc:
        logger.error("Manual product pipeline failed for niche_id=%s: %s", niche_id_str, exc)


async def _dispatch(niche_id_str: str, mode: str) -> None:
    tasks = []
    if mode in ("content", "both"):
        tasks.append(_run_content_pipeline(niche_id_str))
    if mode in ("product", "both"):
        tasks.append(_run_product_pipeline(niche_id_str))
    await asyncio.gather(*tasks)


@router.post("/run/{niche_id}", response_model=RunPipelineResponse, status_code=202)
async def run_pipeline(
    niche_id: str,
    body: RunPipelineRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> RunPipelineResponse:
    if body.mode not in ("content", "product", "both"):
        raise HTTPException(
            status_code=422,
            detail={"code": "INVALID_MODE", "message": "mode must be 'content', 'product', or 'both'"},
        )

    try:
        niche_uuid = UUID(niche_id)
    except ValueError:
        raise HTTPException(status_code=422, detail={"code": "INVALID_UUID", "message": "niche_id is not a valid UUID"})

    repo = SQLNicheRepository(session)
    niche = await repo.find_by_id(NicheId(niche_uuid))
    if niche is None:
        raise HTTPException(status_code=404, detail="Niche not found")

    background_tasks.add_task(_dispatch, niche_id, body.mode)

    return RunPipelineResponse(status="started", niche_id=niche_id, mode=body.mode)

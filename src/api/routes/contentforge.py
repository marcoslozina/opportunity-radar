"""ContentForge integration endpoints.

Exposes the Opportunity Radar data feed so ContentForge's /ideas dashboard
can consume opportunities via a standard REST contract.

Endpoints
---------
GET  /api/v1/feed?limit=N   — paginated list of top opportunities across all niches
POST /api/v1/notify          — accept inbound event notifications from ContentForge
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.models import BriefingModel, NicheModel, OpportunityModel
from infrastructure.db.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["contentforge"])


# ── Feed response schema ──────────────────────────────────────────────────────


class FeedItem(BaseModel):
    id: str
    title: str
    summary: str
    url: str
    product: str
    tags: list[str]
    published_at: str


class FeedResponse(BaseModel):
    items: list[FeedItem]


# ── GET /api/v1/feed ─────────────────────────────────────────────────────────


@router.get("/feed", response_model=FeedResponse)
async def get_feed(
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> FeedResponse:
    """Return the latest top opportunities across all niches.

    Each item maps to the ContentForge feed contract:
    - id:           opportunity UUID
    - title:        opportunity topic
    - summary:      recommended_action (concise, executable insight)
    - url:          direct link to the briefing endpoint for this niche
    - product:      "opportunity-radar"
    - tags:         [niche_name, confidence, domain_applicability (if set)]
    - published_at: ISO-8601 timestamp of briefing generation
    """
    # Fetch the latest briefing per niche, joining opportunities sorted by score
    stmt = (
        select(OpportunityModel, BriefingModel, NicheModel)
        .join(BriefingModel, OpportunityModel.briefing_id == BriefingModel.id)
        .join(NicheModel, BriefingModel.niche_id == NicheModel.id)
        .where(NicheModel.active.is_(True))
        .order_by(OpportunityModel.total.desc())
        .limit(limit)
    )

    rows = await session.execute(stmt)

    items: list[FeedItem] = []
    for opp, briefing, niche in rows:
        tags = [niche.name, opp.confidence]
        if opp.domain_applicability:
            tags.append(opp.domain_applicability)

        items.append(
            FeedItem(
                id=opp.id,
                title=opp.topic,
                summary=opp.recommended_action or opp.topic,
                url=f"/briefing/{briefing.niche_id}",
                product="opportunity-radar",
                tags=tags,
                published_at=briefing.generated_at.isoformat(),
            )
        )

    return FeedResponse(items=items)


# ── POST /api/v1/notify ──────────────────────────────────────────────────────


@router.post("/notify", status_code=200)
async def notify(body: dict[str, Any]) -> dict[str, str]:
    """Accept an inbound event notification from ContentForge.

    ContentForge calls this endpoint when it wants to signal Opportunity Radar
    (e.g., a user triggered a pipeline refresh from the /ideas dashboard).
    The event payload is logged and acknowledged — downstream processing is
    handled asynchronously by the existing pipeline scheduler.
    """
    event_type = body.get("event", "unknown")
    logger.info("contentforge_notify received event=%s keys=%s", event_type, list(body.keys()))
    return {"status": "ok", "event": event_type}

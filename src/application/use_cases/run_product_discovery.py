from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import uuid4

from application.services.profitability_scoring_engine import ProfitabilityScoringEngine
from domain.entities.niche import NicheId
from domain.entities.product_briefing import ProductBriefing
from domain.entities.product_opportunity import ProductOpportunity
from domain.ports.product_discovery_port import ProductDiscoveryPort
from domain.ports.product_repository_ports import ProductBriefingRepository
from domain.ports.repository_ports import NicheRepository
from domain.ports.trend_data_port import TrendDataPort
from domain.value_objects.trend_signal import TrendSignal

logger = logging.getLogger(__name__)


class RunProductDiscoveryUseCase:
    def __init__(
        self,
        niche_repo: NicheRepository,
        product_briefing_repo: ProductBriefingRepository,
        collectors: list[TrendDataPort],
        discovery_port: ProductDiscoveryPort,
        scoring_engine: ProfitabilityScoringEngine,
    ) -> None:
        self._niche_repo = niche_repo
        self._product_briefing_repo = product_briefing_repo
        self._collectors = collectors
        self._discovery_port = discovery_port
        self._scoring_engine = scoring_engine

    async def execute(self, niche_id: NicheId) -> None:
        niche = await self._niche_repo.find_by_id(niche_id)

        signals = await self._collect_all(niche.keywords)
        scores = self._scoring_engine.score(signals)

        opportunities = [
            ProductOpportunity(
                id=str(uuid4()),
                niche_id=str(niche_id),
                topic=topic,
                score=score,
                product_type=None,
                product_reasoning="",
                recommended_price_range="",
                created_at=datetime.now(timezone.utc),
            )
            for topic, score in scores
        ]

        if opportunities:
            classifications = await self._discovery_port.classify(opportunities)
            for opportunity, classification in zip(opportunities, classifications):
                opportunity.product_type = classification.product_type
                opportunity.product_reasoning = classification.reasoning
                opportunity.recommended_price_range = classification.recommended_price_range

        briefing = ProductBriefing(
            id=str(uuid4()),
            niche_id=str(niche_id),
            opportunities=opportunities,
            generated_at=datetime.now(timezone.utc),
        )
        await self._product_briefing_repo.save(briefing)

    async def _collect_all(self, keywords: list[str]) -> list[TrendSignal]:
        tasks = [self._safe_collect(collector, keywords) for collector in self._collectors]
        results = await asyncio.gather(*tasks)
        return [signal for batch in results for signal in batch]

    async def _safe_collect(
        self, collector: TrendDataPort, keywords: list[str]
    ) -> list[TrendSignal]:
        try:
            return await collector.collect(keywords)
        except Exception as exc:
            logger.error(
                "Collector %s failed: %s",
                collector.__class__.__name__,
                exc,
            )
            return []

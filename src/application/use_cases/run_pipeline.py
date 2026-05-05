from __future__ import annotations

import asyncio
import logging

from domain.entities.briefing import Briefing
from domain.entities.niche import NicheId
from domain.entities.opportunity import Opportunity
from domain.ports.insight_port import InsightPort
from domain.ports.repository_ports import BriefingRepository, NicheRepository
from domain.ports.trend_data_port import TrendDataPort
from domain.value_objects.trend_signal import TrendSignal
from application.services.scoring_engine import ScoringEngine

logger = logging.getLogger(__name__)


class NicheNotFoundError(ValueError):
    pass


class RunPipelineUseCase:
    def __init__(
        self,
        niche_repo: NicheRepository,
        briefing_repo: BriefingRepository,
        collectors: list[TrendDataPort],
        insight_port: InsightPort,
    ) -> None:
        self._niche_repo = niche_repo
        self._briefing_repo = briefing_repo
        self._collectors = collectors
        self._insight_port = insight_port

    async def execute(self, niche_id: NicheId) -> Briefing:
        niche = await self._niche_repo.find_by_id(niche_id)
        if niche is None:
            raise NicheNotFoundError(f"Niche {niche_id} not found")

        signals = await self._collect_all(niche.keywords)
        
        # Use factory to get the correct engine
        from application.services.scoring_engine import ScoringFactory
        engine = ScoringFactory.get_engine(niche.discovery_mode)
        scores = engine.score(signals)

        opportunities = [
            Opportunity.create(topic=topic, score=score)
            for topic, score in scores.items()
        ]

        if opportunities:
            await self._insight_port.synthesize(opportunities, niche.discovery_mode)

        briefing = Briefing.create(niche_id=niche_id, opportunities=opportunities)
        await self._briefing_repo.save(briefing)
        return briefing

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

from __future__ import annotations

import logging

from application.services.trajectory_service import TrajectoryService
from domain.entities.briefing import Briefing
from domain.entities.niche import NicheId
from domain.ports.repository_ports import BriefingRepository
from domain.value_objects.score_trajectory import ScoreTrajectory

logger = logging.getLogger(__name__)


class GetBriefingUseCase:
    def __init__(
        self,
        repo: BriefingRepository,
        trajectory_service: TrajectoryService,
    ) -> None:
        self._repo = repo
        self._trajectory_service = trajectory_service

    async def execute(
        self, niche_id: NicheId
    ) -> tuple[Briefing, dict[str, ScoreTrajectory]] | None:
        current = await self._repo.get_latest(niche_id)
        if current is None:
            return None
        try:
            previous = await self._repo.get_previous(niche_id)
        except Exception:
            logger.warning(
                "Failed to fetch previous briefing for niche %s — degrading to no trajectory",
                niche_id,
                exc_info=True,
            )
            previous = None
        trajectory_map = self._trajectory_service.compute(current, previous)
        return current, trajectory_map

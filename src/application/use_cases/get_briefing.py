from __future__ import annotations

from domain.entities.briefing import Briefing
from domain.entities.niche import NicheId
from domain.ports.repository_ports import BriefingRepository


class GetBriefingUseCase:
    def __init__(self, repo: BriefingRepository) -> None:
        self._repo = repo

    async def execute(self, niche_id: NicheId) -> Briefing | None:
        return await self._repo.get_latest(niche_id)

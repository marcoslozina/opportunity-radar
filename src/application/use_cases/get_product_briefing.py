from __future__ import annotations

from domain.entities.product_briefing import ProductBriefing
from domain.ports.product_repository_ports import ProductBriefingRepository


class ProductBriefingNotFoundError(Exception):
    def __init__(self, niche_id: str) -> None:
        self.niche_id = niche_id
        super().__init__(f"No product briefing found for niche '{niche_id}'")


class GetProductBriefingUseCase:
    def __init__(self, product_briefing_repo: ProductBriefingRepository) -> None:
        self._repo = product_briefing_repo

    async def execute(self, niche_id: str) -> ProductBriefing:
        briefing = await self._repo.get_latest(niche_id)
        if briefing is None:
            raise ProductBriefingNotFoundError(niche_id)
        return briefing

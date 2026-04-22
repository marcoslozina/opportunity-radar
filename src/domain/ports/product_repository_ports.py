from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.product_briefing import ProductBriefing
from domain.entities.product_opportunity import ProductOpportunity


class ProductOpportunityRepository(ABC):
    @abstractmethod
    async def save(self, opportunity: ProductOpportunity) -> None: ...

    @abstractmethod
    async def get_by_niche(self, niche_id: str) -> list[ProductOpportunity]: ...


class ProductBriefingRepository(ABC):
    @abstractmethod
    async def save(self, briefing: ProductBriefing) -> None: ...

    @abstractmethod
    async def get_latest(self, niche_id: str) -> ProductBriefing | None: ...

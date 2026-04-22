from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from domain.entities.briefing import Briefing
from domain.entities.niche import Niche, NicheId
from domain.entities.opportunity import Opportunity, OpportunityId


class NicheRepository(ABC):
    @abstractmethod
    async def save(self, niche: Niche) -> None: ...

    @abstractmethod
    async def find_by_id(self, niche_id: NicheId) -> Niche | None: ...

    @abstractmethod
    async def find_all_active(self) -> list[Niche]: ...

    @abstractmethod
    async def delete(self, niche_id: NicheId) -> None: ...


class OpportunityRepository(ABC):
    @abstractmethod
    async def save_bulk(self, opportunities: list[Opportunity], niche_id: NicheId) -> None: ...

    @abstractmethod
    async def find_by_niche(
        self, niche_id: NicheId, cursor: UUID | None = None, limit: int = 20
    ) -> list[Opportunity]: ...


class BriefingRepository(ABC):
    @abstractmethod
    async def save(self, briefing: Briefing) -> None: ...

    @abstractmethod
    async def get_latest(self, niche_id: NicheId) -> Briefing | None: ...

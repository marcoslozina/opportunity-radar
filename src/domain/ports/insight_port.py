from __future__ import annotations

from abc import ABC, abstractmethod

from domain.entities.opportunity import Opportunity


class InsightPort(ABC):
    @abstractmethod
    async def synthesize(self, opportunities: list[Opportunity]) -> list[str]: ...

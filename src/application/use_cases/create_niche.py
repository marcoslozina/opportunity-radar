from __future__ import annotations

from domain.entities.niche import Niche, NicheId
from domain.ports.repository_ports import NicheRepository


class KeywordsRequiredError(ValueError):
    pass


class CreateNicheUseCase:
    def __init__(self, repo: NicheRepository) -> None:
        self._repo = repo

    async def execute(self, name: str, keywords: list[str]) -> Niche:
        if not keywords:
            raise KeywordsRequiredError("At least one keyword is required")

        niche = Niche.create(name=name, keywords=keywords)
        await self._repo.save(niche)
        return niche

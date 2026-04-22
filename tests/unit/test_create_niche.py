from __future__ import annotations

import pytest

from application.use_cases.create_niche import CreateNicheUseCase, KeywordsRequiredError
from domain.entities.niche import Niche, NicheId
from domain.ports.repository_ports import NicheRepository
from uuid import UUID


class FakeNicheRepository(NicheRepository):
    def __init__(self) -> None:
        self.saved: list[Niche] = []

    async def save(self, niche: Niche) -> None:
        self.saved.append(niche)

    async def find_by_id(self, niche_id: NicheId) -> Niche | None:
        return next((n for n in self.saved if n.id == niche_id), None)

    async def find_all_active(self) -> list[Niche]:
        return [n for n in self.saved if n.active]

    async def delete(self, niche_id: NicheId) -> None:
        self.saved = [n for n in self.saved if n.id != niche_id]


async def test_create_niche_when_valid_then_persisted() -> None:
    repo = FakeNicheRepository()
    use_case = CreateNicheUseCase(repo)

    niche = await use_case.execute(name="Angular", keywords=["angular signals", "angular 17"])

    assert niche.name == "Angular"
    assert len(repo.saved) == 1
    assert repo.saved[0].id == niche.id


async def test_create_niche_when_empty_keywords_then_raises() -> None:
    repo = FakeNicheRepository()
    use_case = CreateNicheUseCase(repo)

    with pytest.raises(KeywordsRequiredError):
        await use_case.execute(name="Angular", keywords=[])

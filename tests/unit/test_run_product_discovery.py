from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from application.services.profitability_scoring_engine import ProfitabilityScoringEngine
from application.use_cases.run_product_discovery import RunProductDiscoveryUseCase
from domain.entities.niche import Niche, NicheId
from domain.entities.product_briefing import ProductBriefing
from domain.entities.product_opportunity import ProductOpportunity
from domain.ports.product_discovery_port import ProductClassification, ProductDiscoveryPort
from domain.ports.product_repository_ports import ProductBriefingRepository
from domain.ports.repository_ports import NicheRepository
from domain.ports.trend_data_port import TrendDataPort
from domain.value_objects.product_type import ProductType
from domain.value_objects.trend_signal import TrendSignal

_NOW = datetime.now(tz=timezone.utc)


class FakeNicheRepository(NicheRepository):
    def __init__(self, niche: Niche) -> None:
        self._niche = niche

    async def save(self, niche: Niche) -> None: ...
    async def find_all_active(self) -> list[Niche]: return [self._niche]
    async def delete(self, niche_id: NicheId) -> None: ...

    async def find_by_id(self, niche_id: NicheId) -> Niche | None:
        return self._niche if self._niche.id == niche_id else None


class FakeProductBriefingRepository(ProductBriefingRepository):
    def __init__(self) -> None:
        self.saved: list[ProductBriefing] = []

    async def save(self, briefing: ProductBriefing) -> None:
        self.saved.append(briefing)

    async def get_latest(self, niche_id: str) -> ProductBriefing | None:
        return next((b for b in reversed(self.saved) if b.niche_id == niche_id), None)


class OkAdapter(TrendDataPort):
    async def collect(self, keywords: list[str]) -> list[TrendSignal]:
        return [
            TrendSignal(
                source="ok",
                topic=kw,
                raw_value=0.5,
                signal_type="frustration_level",
                collected_at=_NOW,
            )
            for kw in keywords
        ]


class FailingAdapter(TrendDataPort):
    async def collect(self, keywords: list[str]) -> list[TrendSignal]:
        raise RuntimeError("adapter down")


class FakeProductDiscoveryPort(ProductDiscoveryPort):
    async def classify(
        self, opportunities: list[ProductOpportunity]
    ) -> list[ProductClassification]:
        return [
            ProductClassification(
                product_type=ProductType.EBOOK,
                reasoning="great ebook opportunity",
                recommended_price_range="$19–$49",
            )
            for _ in opportunities
        ]


async def test_pipeline_continues_if_one_adapter_fails() -> None:
    niche = Niche.create("Python", ["python testing", "python async"])
    niche_repo = FakeNicheRepository(niche)
    briefing_repo = FakeProductBriefingRepository()

    use_case = RunProductDiscoveryUseCase(
        niche_repo=niche_repo,
        product_briefing_repo=briefing_repo,
        collectors=[OkAdapter(), FailingAdapter(), OkAdapter()],
        discovery_port=FakeProductDiscoveryPort(),
        scoring_engine=ProfitabilityScoringEngine(),
    )

    await use_case.execute(niche.id)

    assert len(briefing_repo.saved) == 1


async def test_pipeline_saves_briefing_with_classifications() -> None:
    niche = Niche.create("Python", ["python testing"])
    niche_repo = FakeNicheRepository(niche)
    briefing_repo = FakeProductBriefingRepository()

    use_case = RunProductDiscoveryUseCase(
        niche_repo=niche_repo,
        product_briefing_repo=briefing_repo,
        collectors=[OkAdapter()],
        discovery_port=FakeProductDiscoveryPort(),
        scoring_engine=ProfitabilityScoringEngine(),
    )

    await use_case.execute(niche.id)

    saved = briefing_repo.saved[0]
    assert len(saved.opportunities) == 1
    assert saved.opportunities[0].product_type == ProductType.EBOOK

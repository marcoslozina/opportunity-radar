from __future__ import annotations

from datetime import datetime, timezone

from application.services.scoring_engine import ScoringEngine
from application.use_cases.run_pipeline import RunPipelineUseCase
from domain.entities.briefing import Briefing
from domain.entities.niche import Niche, NicheId
from domain.entities.opportunity import Opportunity
from domain.ports.insight_port import InsightPort
from domain.ports.repository_ports import BriefingRepository, NicheRepository
from domain.ports.trend_data_port import TrendDataPort
from domain.value_objects.trend_signal import TrendSignal
from uuid import uuid4

_NOW = datetime.now(tz=timezone.utc)


class FakeNicheRepository(NicheRepository):
    def __init__(self, niche: Niche) -> None:
        self._niche = niche

    async def save(self, niche: Niche) -> None: ...
    async def find_all_active(self) -> list[Niche]: return [self._niche]
    async def delete(self, niche_id: NicheId) -> None: ...

    async def find_by_id(self, niche_id: NicheId) -> Niche | None:
        return self._niche if self._niche.id == niche_id else None


class FakeBriefingRepository(BriefingRepository):
    def __init__(self) -> None:
        self.saved: list[Briefing] = []

    async def save(self, briefing: Briefing) -> None:
        self.saved.append(briefing)

    async def get_latest(self, niche_id: NicheId) -> Briefing | None:
        return next((b for b in reversed(self.saved) if b.niche_id == niche_id), None)


class OkAdapter(TrendDataPort):
    async def collect(self, keywords: list[str]) -> list[TrendSignal]:
        return [
            TrendSignal(source="ok", topic=kw, raw_value=0.5, signal_type="trend_velocity", collected_at=_NOW)
            for kw in keywords
        ]


class FailingAdapter(TrendDataPort):
    async def collect(self, keywords: list[str]) -> list[TrendSignal]:
        raise RuntimeError("API down")


class FakeInsightPort(InsightPort):
    async def synthesize(self, opportunities: list[Opportunity]) -> list[str]:
        return ["Crear contenido" for _ in opportunities]


async def test_run_pipeline_when_one_adapter_fails_then_pipeline_completes() -> None:
    niche = Niche.create("Angular", ["angular signals"])
    niche_repo = FakeNicheRepository(niche)
    briefing_repo = FakeBriefingRepository()

    use_case = RunPipelineUseCase(
        niche_repo=niche_repo,
        briefing_repo=briefing_repo,
        collectors=[OkAdapter(), FailingAdapter()],
        insight_port=FakeInsightPort(),
        scoring_engine=ScoringEngine(),
    )

    briefing = await use_case.execute(niche.id)

    assert briefing is not None
    assert len(briefing_repo.saved) == 1


async def test_run_pipeline_when_all_ok_then_briefing_has_opportunities() -> None:
    niche = Niche.create("Angular", ["angular signals", "angular 17"])
    niche_repo = FakeNicheRepository(niche)
    briefing_repo = FakeBriefingRepository()

    use_case = RunPipelineUseCase(
        niche_repo=niche_repo,
        briefing_repo=briefing_repo,
        collectors=[OkAdapter()],
        insight_port=FakeInsightPort(),
        scoring_engine=ScoringEngine(),
    )

    briefing = await use_case.execute(niche.id)

    assert len(briefing.opportunities) == 2
    assert all(o.recommended_action == "Crear contenido" for o in briefing.opportunities)

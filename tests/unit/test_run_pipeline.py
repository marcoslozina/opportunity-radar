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
from domain.value_objects.evidence_item import EvidenceItem
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

    async def get_previous(self, niche_id: NicheId) -> Briefing | None:
        matches = [b for b in self.saved if b.niche_id == niche_id]
        return matches[-2] if len(matches) >= 2 else None


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
    async def synthesize(self, opportunities: list[Opportunity], discovery_mode: str) -> None:
        for opp in opportunities:
            opp.recommended_action = "Crear contenido"


async def test_run_pipeline_when_one_adapter_fails_then_pipeline_completes() -> None:
    niche = Niche.create("Angular", ["angular signals"])
    niche_repo = FakeNicheRepository(niche)
    briefing_repo = FakeBriefingRepository()

    use_case = RunPipelineUseCase(
        niche_repo=niche_repo,
        briefing_repo=briefing_repo,
        collectors=[OkAdapter(), FailingAdapter()],
        insight_port=FakeInsightPort(),
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
    )

    briefing = await use_case.execute(niche.id)

    assert len(briefing.opportunities) == 2
    assert all(o.recommended_action == "Crear contenido" for o in briefing.opportunities)


def _make_evidence_item(topic: str, signal_type: str = "social_signal", engagement_count: int = 100) -> EvidenceItem:
    return EvidenceItem(
        source="test",
        signal_type=signal_type,
        topic=topic,
        title=f"Test item for {topic}",
        url=None,
        engagement_count=engagement_count,
        engagement_label="upvotes",
        collected_at=_NOW,
    )


class AdapterWithEvidence(TrendDataPort):
    """Adapter that populates _last_evidence after collect()."""
    def __init__(self, keyword: str, evidence: list[EvidenceItem]) -> None:
        self._keyword = keyword
        self._evidence_to_emit = evidence
        self._last_evidence: list[EvidenceItem] = []

    async def collect(self, keywords: list[str]) -> list[TrendSignal]:
        self._last_evidence = self._evidence_to_emit
        return [
            TrendSignal(source="test", topic=kw, raw_value=0.5, signal_type="trend_velocity", collected_at=_NOW)
            for kw in keywords
        ]


async def test_execute_attaches_evidence_to_opportunities() -> None:
    keyword = "angular signals"
    niche = Niche.create("Angular", [keyword])
    niche_repo = FakeNicheRepository(niche)
    briefing_repo = FakeBriefingRepository()

    evidence = [_make_evidence_item(topic=keyword, engagement_count=500)]
    adapter = AdapterWithEvidence(keyword, evidence)

    use_case = RunPipelineUseCase(
        niche_repo=niche_repo,
        briefing_repo=briefing_repo,
        collectors=[adapter],
        insight_port=FakeInsightPort(),
    )

    briefing = await use_case.execute(niche.id)

    opp = next(o for o in briefing.opportunities if o.topic == keyword)
    assert len(opp.evidence) == 1
    assert opp.evidence[0].engagement_count == 500


async def test_execute_caps_evidence_at_15_per_opportunity() -> None:
    keyword = "test topic"
    niche = Niche.create("Test", [keyword])
    niche_repo = FakeNicheRepository(niche)
    briefing_repo = FakeBriefingRepository()

    # 20 items of the same signal_type — only top 5 per type kept, then capped at 15 total
    evidence = [_make_evidence_item(topic=keyword, engagement_count=i) for i in range(20)]
    adapter = AdapterWithEvidence(keyword, evidence)

    use_case = RunPipelineUseCase(
        niche_repo=niche_repo,
        briefing_repo=briefing_repo,
        collectors=[adapter],
        insight_port=FakeInsightPort(),
    )

    briefing = await use_case.execute(niche.id)

    opp = next(o for o in briefing.opportunities if o.topic == keyword)
    assert len(opp.evidence) <= 15


async def test_execute_caps_evidence_at_5_per_signal_type() -> None:
    keyword = "test topic"
    niche = Niche.create("Test", [keyword])
    niche_repo = FakeNicheRepository(niche)
    briefing_repo = FakeBriefingRepository()

    # 8 items of the same signal_type — only top 5 should remain
    evidence = [_make_evidence_item(topic=keyword, signal_type="social_signal", engagement_count=i) for i in range(8)]
    adapter = AdapterWithEvidence(keyword, evidence)

    use_case = RunPipelineUseCase(
        niche_repo=niche_repo,
        briefing_repo=briefing_repo,
        collectors=[adapter],
        insight_port=FakeInsightPort(),
    )

    briefing = await use_case.execute(niche.id)

    opp = next(o for o in briefing.opportunities if o.topic == keyword)
    assert len(opp.evidence) == 5
    # top 5 by engagement_count descending: [7, 6, 5, 4, 3]
    assert opp.evidence[0].engagement_count == 7


async def test_execute_works_when_adapter_has_no_last_evidence() -> None:
    """Adapter without _last_evidence attribute — pipeline completes, evidence is []."""
    niche = Niche.create("Angular", ["angular signals"])
    niche_repo = FakeNicheRepository(niche)
    briefing_repo = FakeBriefingRepository()

    use_case = RunPipelineUseCase(
        niche_repo=niche_repo,
        briefing_repo=briefing_repo,
        collectors=[OkAdapter()],  # OkAdapter has no _last_evidence
        insight_port=FakeInsightPort(),
    )

    briefing = await use_case.execute(niche.id)

    assert briefing is not None
    for opp in briefing.opportunities:
        assert opp.evidence == []

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import pytest

from application.services.trajectory_service import TrajectoryService
from application.use_cases.get_briefing import GetBriefingUseCase
from domain.entities.briefing import Briefing
from domain.entities.niche import NicheId
from domain.entities.opportunity import Opportunity
from domain.ports.repository_ports import BriefingRepository
from domain.value_objects.opportunity_score import OpportunityScore

_NICHE_ID = NicheId(uuid4())
_PREV_DATE = datetime(2026, 4, 28, 8, 0, 0)
_CURR_DATE = datetime(2026, 5, 5, 8, 0, 0)


def _make_score(total: float) -> OpportunityScore:
    return OpportunityScore(
        trend_velocity=5.0,
        competition_gap=5.0,
        social_signal=5.0,
        monetization_intent=5.0,
        frustration_level=5.0,
        total=total,
        confidence="medium",
    )


def _make_briefing(topics: dict[str, float], generated_at: datetime) -> Briefing:
    opportunities = [
        Opportunity.create(topic=topic, score=_make_score(total))
        for topic, total in topics.items()
    ]
    b = Briefing.create(niche_id=_NICHE_ID, opportunities=opportunities)
    object.__setattr__(b, "generated_at", generated_at)
    return b


class FakeBriefingRepository(BriefingRepository):
    def __init__(
        self,
        current: Briefing | None,
        previous: Briefing | None,
        raise_on_previous: bool = False,
    ) -> None:
        self._current = current
        self._previous = previous
        self._raise_on_previous = raise_on_previous

    async def save(self, briefing: Briefing) -> None: ...

    async def get_latest(self, niche_id: NicheId) -> Briefing | None:
        return self._current

    async def get_previous(self, niche_id: NicheId) -> Briefing | None:
        if self._raise_on_previous:
            raise RuntimeError("DB timeout")
        return self._previous


async def test_execute_when_no_briefing_then_returns_none() -> None:
    repo = FakeBriefingRepository(current=None, previous=None)
    use_case = GetBriefingUseCase(repo=repo, trajectory_service=TrajectoryService())

    result = await use_case.execute(_NICHE_ID)

    assert result is None


async def test_execute_when_briefing_exists_then_returns_tuple() -> None:
    current = _make_briefing({"Topic A": 7.0}, _CURR_DATE)
    previous = _make_briefing({"Topic A": 5.0}, _PREV_DATE)
    repo = FakeBriefingRepository(current=current, previous=previous)
    use_case = GetBriefingUseCase(repo=repo, trajectory_service=TrajectoryService())

    result = await use_case.execute(_NICHE_ID)

    assert result is not None
    briefing, trajectory_map = result
    assert briefing is current
    assert "topic a" in trajectory_map


async def test_execute_when_previous_is_none_then_empty_trajectory() -> None:
    current = _make_briefing({"Topic A": 7.0}, _CURR_DATE)
    repo = FakeBriefingRepository(current=current, previous=None)
    use_case = GetBriefingUseCase(repo=repo, trajectory_service=TrajectoryService())

    result = await use_case.execute(_NICHE_ID)

    assert result is not None
    briefing, trajectory_map = result
    assert trajectory_map == {}


async def test_execute_when_get_previous_raises_then_degrades_gracefully() -> None:
    current = _make_briefing({"Topic A": 7.0}, _CURR_DATE)
    repo = FakeBriefingRepository(current=current, previous=None, raise_on_previous=True)
    use_case = GetBriefingUseCase(repo=repo, trajectory_service=TrajectoryService())

    result = await use_case.execute(_NICHE_ID)

    assert result is not None
    briefing, trajectory_map = result
    assert briefing is current
    assert trajectory_map == {}


async def test_execute_trajectory_map_contains_correct_delta() -> None:
    current = _make_briefing({"Topic A": 8.0}, _CURR_DATE)
    previous = _make_briefing({"Topic A": 5.0}, _PREV_DATE)
    repo = FakeBriefingRepository(current=current, previous=previous)
    use_case = GetBriefingUseCase(repo=repo, trajectory_service=TrajectoryService())

    result = await use_case.execute(_NICHE_ID)

    assert result is not None
    _, trajectory_map = result
    t = trajectory_map["topic a"]
    assert t.delta == 3.0
    assert t.direction == "GROWING ↑"
    assert t.compared_at == _PREV_DATE

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from application.services.trajectory_service import TrajectoryService
from domain.entities.briefing import Briefing
from domain.entities.niche import NicheId
from domain.entities.opportunity import Opportunity
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
    briefing = Briefing.create(niche_id=_NICHE_ID, opportunities=opportunities)
    object.__setattr__(briefing, "generated_at", generated_at)
    return briefing


def test_compute_when_previous_is_none_then_returns_empty_dict() -> None:
    service = TrajectoryService()
    current = _make_briefing({"Topic A": 7.0}, _CURR_DATE)

    result = service.compute(current, previous=None)

    assert result == {}


def test_compute_when_topic_matches_then_trajectory_is_computed() -> None:
    service = TrajectoryService()
    previous = _make_briefing({"Topic A": 5.0}, _PREV_DATE)
    current = _make_briefing({"Topic A": 7.5}, _CURR_DATE)

    result = service.compute(current, previous)

    assert "topic a" in result
    t = result["topic a"]
    assert t.delta == 2.5
    assert t.direction == "GROWING ↑"
    assert t.compared_at == _PREV_DATE


def test_compute_when_topic_missing_in_previous_then_key_absent() -> None:
    service = TrajectoryService()
    previous = _make_briefing({"Topic A": 5.0}, _PREV_DATE)
    current = _make_briefing({"Topic A": 7.5, "New Topic": 6.0}, _CURR_DATE)

    result = service.compute(current, previous)

    assert "topic a" in result
    assert "new topic" not in result


def test_compute_topic_matching_is_case_insensitive_and_strips_whitespace() -> None:
    service = TrajectoryService()
    # delta_pct = (8.2 - 8.0) / 8.0 * 100 = 2.5% → STABLE
    previous = _make_briefing({"  Crédito Hipotecario  ": 8.0}, _PREV_DATE)
    current = _make_briefing({"crédito hipotecario": 8.2}, _CURR_DATE)

    result = service.compute(current, previous)

    assert "crédito hipotecario" in result
    assert result["crédito hipotecario"].direction == "STABLE →"


def test_compute_returns_trajectories_for_all_matching_topics() -> None:
    service = TrajectoryService()
    previous = _make_briefing({"Topic A": 5.0, "Topic B": 8.0, "Topic C": 6.0}, _PREV_DATE)
    current = _make_briefing({"Topic A": 7.5, "Topic B": 6.5, "Topic D": 9.0}, _CURR_DATE)

    result = service.compute(current, previous)

    assert "topic a" in result
    assert "topic b" in result
    assert "topic d" not in result  # not in previous
    assert "topic c" not in result  # not in current

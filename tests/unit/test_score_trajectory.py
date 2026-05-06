from __future__ import annotations

from datetime import datetime

from domain.value_objects.score_trajectory import ScoreTrajectory

_COMPARED_AT = datetime(2026, 4, 28, 8, 0, 0)


def test_compute_when_score_grows_then_direction_is_growing() -> None:
    t = ScoreTrajectory.compute(
        current_total=7.2,
        previous_total=5.1,
        compared_at=_COMPARED_AT,
    )
    assert t.direction == "GROWING ↑"
    assert t.delta == 2.1
    assert t.delta_pct > 5.0


def test_compute_when_score_cools_then_direction_is_cooling() -> None:
    t = ScoreTrajectory.compute(
        current_total=6.5,
        previous_total=8.0,
        compared_at=_COMPARED_AT,
    )
    assert t.direction == "COOLING ↓"
    assert t.delta == -1.5
    assert t.delta_pct == -18.75


def test_compute_when_score_stable_then_direction_is_stable() -> None:
    t = ScoreTrajectory.compute(
        current_total=6.2,
        previous_total=6.0,
        compared_at=_COMPARED_AT,
    )
    assert t.direction == "STABLE →"
    assert t.delta_pct < 5.0
    assert t.delta_pct > -5.0


def test_compute_when_previous_total_is_zero_then_delta_pct_is_zero() -> None:
    t = ScoreTrajectory.compute(
        current_total=5.0,
        previous_total=0.0,
        compared_at=_COMPARED_AT,
    )
    assert t.delta_pct == 0.0
    assert t.direction == "STABLE →"


def test_compute_delta_and_delta_pct_are_rounded_to_2_decimal_places() -> None:
    t = ScoreTrajectory.compute(
        current_total=7.2,
        previous_total=5.1,
        compared_at=_COMPARED_AT,
    )
    # delta = 7.2 - 5.1 = 2.1 (exact at 2dp), delta_pct = 2.1/5.1*100 = 41.176...
    assert t.delta == round(t.delta, 2)
    assert t.delta_pct == round(t.delta_pct, 2)


def test_compute_exact_growing_boundary() -> None:
    # delta_pct exactly 5.0 -> GROWING
    t = ScoreTrajectory.compute(
        current_total=105.0,
        previous_total=100.0,
        compared_at=_COMPARED_AT,
    )
    assert t.direction == "GROWING ↑"
    assert t.delta_pct == 5.0


def test_compute_exact_cooling_boundary() -> None:
    # delta_pct exactly -5.0 -> COOLING
    t = ScoreTrajectory.compute(
        current_total=95.0,
        previous_total=100.0,
        compared_at=_COMPARED_AT,
    )
    assert t.direction == "COOLING ↓"
    assert t.delta_pct == -5.0


def test_compute_previous_total_and_compared_at_stored_correctly() -> None:
    t = ScoreTrajectory.compute(
        current_total=7.0,
        previous_total=5.1,
        compared_at=_COMPARED_AT,
    )
    assert t.previous_total == 5.1
    assert t.compared_at == _COMPARED_AT

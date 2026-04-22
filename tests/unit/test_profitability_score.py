from __future__ import annotations

from domain.value_objects.profitability_score import ProfitabilityScore


def test_from_dimensions_calculates_total() -> None:
    score = ProfitabilityScore.from_dimensions(
        frustration_level=5.0,
        market_size=4.0,
        competition_gap=6.0,
        willingness_to_pay=3.0,
    )
    assert 0 <= score.total <= 100


def test_from_dimensions_confidence_high() -> None:
    score = ProfitabilityScore.from_dimensions(
        frustration_level=7.0,
        market_size=5.0,
        competition_gap=6.0,
        willingness_to_pay=4.0,
    )
    assert score.confidence == "high"


def test_from_dimensions_confidence_medium() -> None:
    score = ProfitabilityScore.from_dimensions(
        frustration_level=7.0,
        market_size=5.0,
        competition_gap=0.0,
        willingness_to_pay=0.0,
    )
    assert score.confidence == "medium"


def test_from_dimensions_confidence_low() -> None:
    score = ProfitabilityScore.from_dimensions(
        frustration_level=7.0,
        market_size=0.0,
        competition_gap=0.0,
        willingness_to_pay=0.0,
    )
    assert score.confidence == "low"


def test_total_capped_at_100() -> None:
    score = ProfitabilityScore.from_dimensions(
        frustration_level=10.0,
        market_size=10.0,
        competition_gap=10.0,
        willingness_to_pay=10.0,
    )
    assert score.total == 100.0


def test_total_floor_at_0() -> None:
    score = ProfitabilityScore.from_dimensions(
        frustration_level=0.0,
        market_size=0.0,
        competition_gap=0.0,
        willingness_to_pay=0.0,
    )
    assert score.total == 0.0

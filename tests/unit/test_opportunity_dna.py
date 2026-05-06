from __future__ import annotations

import pytest

from domain.value_objects.opportunity_dna import OpportunityDNA
from domain.value_objects.opportunity_score import OpportunityScore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_score(
    trend_velocity: float = 5.0,
    competition_gap: float = 5.0,
    social_signal: float = 5.0,
    monetization_intent: float = 5.0,
    frustration_level: float = 5.0,
    total: float = 50.0,
    confidence: str = "medium",
) -> OpportunityScore:
    return OpportunityScore(
        trend_velocity=trend_velocity,
        competition_gap=competition_gap,
        social_signal=social_signal,
        monetization_intent=monetization_intent,
        frustration_level=frustration_level,
        total=total,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Archetype classification
# ---------------------------------------------------------------------------

def test_archetype_when_high_competition_gap_and_monetization_then_blue_ocean() -> None:
    score = _make_score(competition_gap=8.5, monetization_intent=7.2)
    dna = OpportunityDNA.from_score(score)
    assert dna.archetype == "Blue Ocean"
    assert dna.dominant_signal == "competition_gap"


def test_archetype_when_high_frustration_and_social_then_pain_point() -> None:
    score = _make_score(frustration_level=8.0, social_signal=7.0,
                        competition_gap=4.0, monetization_intent=4.0, trend_velocity=4.0)
    dna = OpportunityDNA.from_score(score)
    assert dna.archetype == "Pain Point"
    assert dna.dominant_signal == "frustration_level"


def test_archetype_when_high_trend_velocity_and_low_competition_then_trend_play() -> None:
    score = _make_score(trend_velocity=8.5, competition_gap=5.0,
                        social_signal=4.0, monetization_intent=4.0, frustration_level=4.0)
    dna = OpportunityDNA.from_score(score)
    assert dna.archetype == "Trend Play"
    assert dna.dominant_signal == "trend_velocity"


def test_archetype_when_niche_gap_and_frustration_then_niche_dominator() -> None:
    score = _make_score(competition_gap=7.0, frustration_level=6.5,
                        monetization_intent=4.0, trend_velocity=4.0, social_signal=4.0)
    dna = OpportunityDNA.from_score(score)
    assert dna.archetype == "Niche Dominator"
    assert dna.dominant_signal == "competition_gap"


def test_archetype_when_all_mid_range_then_emerging() -> None:
    score = _make_score(trend_velocity=5.0, competition_gap=5.0, social_signal=5.0,
                        monetization_intent=5.0, frustration_level=5.0)
    dna = OpportunityDNA.from_score(score)
    assert dna.archetype == "Emerging"


def test_archetype_when_all_low_then_weak_signal() -> None:
    score = _make_score(trend_velocity=2.0, competition_gap=2.0, social_signal=2.0,
                        monetization_intent=2.0, frustration_level=2.0)
    dna = OpportunityDNA.from_score(score)
    assert dna.archetype == "Weak Signal"


def test_blue_ocean_takes_priority_over_niche_dominator() -> None:
    # Both Blue Ocean and Niche Dominator conditions are met — Blue Ocean wins
    score = _make_score(competition_gap=8.0, monetization_intent=7.5, frustration_level=6.5)
    dna = OpportunityDNA.from_score(score)
    assert dna.archetype == "Blue Ocean"


# ---------------------------------------------------------------------------
# dominant_signal
# ---------------------------------------------------------------------------

def test_dominant_signal_when_tie_then_resolves_by_tiebreak_order() -> None:
    # All dims equal — tie-break favors trend_velocity
    score = _make_score(trend_velocity=5.0, competition_gap=5.0, social_signal=5.0,
                        monetization_intent=5.0, frustration_level=5.0)
    dna = OpportunityDNA.from_score(score)
    assert dna.dominant_signal == "trend_velocity"


def test_dominant_signal_when_clear_winner_then_returns_that_dimension() -> None:
    score = _make_score(monetization_intent=9.1, trend_velocity=5.0, competition_gap=5.0,
                        social_signal=5.0, frustration_level=5.0)
    dna = OpportunityDNA.from_score(score)
    assert dna.dominant_signal == "monetization_intent"


# ---------------------------------------------------------------------------
# dimensions dict completeness
# ---------------------------------------------------------------------------

def test_dimensions_dict_includes_frustration_level() -> None:
    score = _make_score()
    dna = OpportunityDNA.from_score(score)
    expected_keys = {"trend_velocity", "competition_gap", "social_signal",
                     "monetization_intent", "frustration_level"}
    assert set(dna.dimensions.keys()) == expected_keys


def test_dimensions_dict_values_match_score_fields() -> None:
    score = _make_score(trend_velocity=3.1, competition_gap=4.2, social_signal=5.3,
                        monetization_intent=6.4, frustration_level=7.5)
    dna = OpportunityDNA.from_score(score)
    assert dna.dimensions["trend_velocity"] == 3.1
    assert dna.dimensions["competition_gap"] == 4.2
    assert dna.dimensions["social_signal"] == 5.3
    assert dna.dimensions["monetization_intent"] == 6.4
    assert dna.dimensions["frustration_level"] == 7.5


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------

def test_opportunity_dna_is_frozen() -> None:
    score = _make_score()
    dna = OpportunityDNA.from_score(score)
    with pytest.raises(Exception):  # FrozenInstanceError
        dna.archetype = "Mutated"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Archetype descriptions are non-empty strings
# ---------------------------------------------------------------------------

def test_archetype_description_is_non_empty_for_all_archetypes() -> None:
    scenarios = [
        _make_score(competition_gap=8.5, monetization_intent=7.2),  # Blue Ocean
        _make_score(frustration_level=8.0, social_signal=7.0,
                    competition_gap=4.0, monetization_intent=4.0, trend_velocity=4.0),  # Pain Point
        _make_score(trend_velocity=8.5, competition_gap=5.0,
                    social_signal=4.0, monetization_intent=4.0, frustration_level=4.0),  # Trend Play
        _make_score(competition_gap=7.0, frustration_level=6.5,
                    monetization_intent=4.0, trend_velocity=4.0, social_signal=4.0),  # Niche Dominator
        _make_score(),  # Emerging
        _make_score(trend_velocity=2.0, competition_gap=2.0, social_signal=2.0,
                    monetization_intent=2.0, frustration_level=2.0),  # Weak Signal
    ]
    for score in scenarios:
        dna = OpportunityDNA.from_score(score)
        assert dna.archetype_description, f"Description empty for archetype: {dna.archetype}"

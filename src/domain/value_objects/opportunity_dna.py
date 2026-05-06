from __future__ import annotations

from dataclasses import dataclass

from domain.value_objects.opportunity_score import OpportunityScore

# ---------------------------------------------------------------------------
# Threshold constants — pure Python, no external config
# ---------------------------------------------------------------------------
_BLUE_OCEAN_COMPETITION_MIN = 7.0
_BLUE_OCEAN_MONETIZATION_MIN = 7.0
_PAIN_POINT_FRUSTRATION_MIN = 7.0
_PAIN_POINT_SOCIAL_MIN = 6.5
_TREND_PLAY_VELOCITY_MIN = 7.5
_NICHE_DOM_COMPETITION_MIN = 6.5
_NICHE_DOM_FRUSTRATION_MIN = 6.0
_EMERGING_LOW = 3.5
_EMERGING_HIGH = 7.0

# Tie-break order for dominant_signal (index = priority, lower = higher priority)
_TIE_BREAK_ORDER = [
    "trend_velocity",
    "competition_gap",
    "monetization_intent",
    "social_signal",
    "frustration_level",
]


def _classify(dims: dict[str, float]) -> tuple[str, str]:
    cg = dims["competition_gap"]
    mi = dims["monetization_intent"]
    fl = dims["frustration_level"]
    ss = dims["social_signal"]
    tv = dims["trend_velocity"]

    if cg >= _BLUE_OCEAN_COMPETITION_MIN and mi >= _BLUE_OCEAN_MONETIZATION_MIN:
        return "Blue Ocean", "High demand, low competition, strong monetization potential"

    if fl >= _PAIN_POINT_FRUSTRATION_MIN and ss >= _PAIN_POINT_SOCIAL_MIN:
        return "Pain Point", "Clear user pain backed by strong community signal"

    if tv >= _TREND_PLAY_VELOCITY_MIN and tv > cg:
        return "Trend Play", "Fast-moving topic with momentum; competition hasn't caught up yet"

    if cg >= _NICHE_DOM_COMPETITION_MIN and fl >= _NICHE_DOM_FRUSTRATION_MIN:
        return "Niche Dominator", "Underserved niche with tangible user frustration to solve"

    all_values = list(dims.values())
    if all(v >= _EMERGING_LOW for v in all_values) and all(v < _EMERGING_HIGH for v in all_values):
        return "Emerging", "Balanced, promising signal across all dimensions — still early"

    return "Weak Signal", "Mixed or low signals; requires more data before acting"


def _dominant_signal(dims: dict[str, float]) -> str:
    max_val = max(dims.values())
    # Among all keys tied at max_val, pick the one with highest tie-break priority
    candidates = [k for k, v in dims.items() if v == max_val]
    for key in _TIE_BREAK_ORDER:
        if key in candidates:
            return key
    return candidates[0]  # fallback — should never reach here


@dataclass(frozen=True)
class OpportunityDNA:
    archetype: str
    archetype_description: str
    dimensions: dict[str, float]  # all 5 dimension values
    dominant_signal: str

    @classmethod
    def from_score(cls, score: OpportunityScore) -> OpportunityDNA:
        dims: dict[str, float] = {
            "trend_velocity": score.trend_velocity,
            "competition_gap": score.competition_gap,
            "social_signal": score.social_signal,
            "monetization_intent": score.monetization_intent,
            "frustration_level": score.frustration_level,
        }
        archetype, description = _classify(dims)
        dominant = _dominant_signal(dims)
        return cls(
            archetype=archetype,
            archetype_description=description,
            dimensions=dims,
            dominant_signal=dominant,
        )

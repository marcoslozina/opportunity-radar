# Design — opportunity-dna

## Layer Decision

**DNA computation lives in the domain value object layer, invoked at API response assembly time.**

This follows the same pattern as `ScoreTrajectory` (computed by `TrajectoryService` at read time, never stored). DNA is a pure derivation of `OpportunityScore` — storing it would be redundant and require a DB migration that delivers zero new information.

---

## New Artifact: `OpportunityDNA` (domain value object)

**File:** `src/domain/value_objects/opportunity_dna.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from domain.value_objects.opportunity_score import OpportunityScore

# Thresholds — define as module-level constants for easy testing and future tuning
_BLUE_OCEAN_COMPETITION_MIN   = 7.0
_BLUE_OCEAN_MONETIZATION_MIN  = 7.0
_PAIN_POINT_FRUSTRATION_MIN   = 7.0
_PAIN_POINT_SOCIAL_MIN        = 6.5
_TREND_PLAY_VELOCITY_MIN      = 7.5
_NICHE_DOM_COMPETITION_MIN    = 6.5
_NICHE_DOM_FRUSTRATION_MIN    = 6.0
_EMERGING_LOW                 = 3.5
_EMERGING_HIGH                = 7.0

# Tie-break order for dominant_signal (index = priority, lower = higher priority)
_TIE_BREAK_ORDER = [
    "trend_velocity",
    "competition_gap",
    "monetization_intent",
    "social_signal",
    "frustration_level",
]


@dataclass(frozen=True)
class OpportunityDNA:
    archetype: str
    archetype_description: str
    dimensions: dict[str, float]   # all 5 dims
    dominant_signal: str

    @classmethod
    def from_score(cls, score: OpportunityScore) -> OpportunityDNA:
        dims = {
            "trend_velocity":     score.trend_velocity,
            "competition_gap":    score.competition_gap,
            "social_signal":      score.social_signal,
            "monetization_intent": score.monetization_intent,
            "frustration_level":  score.frustration_level,
        }
        archetype, description = _classify(dims)
        dominant = _dominant_signal(dims)
        return cls(
            archetype=archetype,
            archetype_description=description,
            dimensions=dims,
            dominant_signal=dominant,
        )
```

### Archetype classification (private function)

```python
def _classify(dims: dict[str, float]) -> tuple[str, str]:
    cg  = dims["competition_gap"]
    mi  = dims["monetization_intent"]
    fl  = dims["frustration_level"]
    ss  = dims["social_signal"]
    tv  = dims["trend_velocity"]

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
```

### Dominant signal resolution (private function)

```python
def _dominant_signal(dims: dict[str, float]) -> str:
    max_val = max(dims.values())
    # Among all keys with the max value, pick the one with highest tie-break priority
    candidates = [k for k, v in dims.items() if v == max_val]
    for key in _TIE_BREAK_ORDER:
        if key in candidates:
            return key
    return candidates[0]   # fallback — should never reach here
```

---

## API Schema additions

**File:** `src/api/schemas/opportunity.py` — add two new classes:

```python
class DimensionsResponse(BaseModel):
    trend_velocity: float
    competition_gap: float
    social_signal: float
    monetization_intent: float
    frustration_level: float   # now exposed in DNA — previously omitted

class OpportunityDNAResponse(BaseModel):
    archetype: str
    archetype_description: str
    dimensions: DimensionsResponse
    dominant_signal: str
```

Update `OpportunityResponse`:

```python
class OpportunityResponse(BaseModel):
    id: str
    topic: str
    score: OpportunityScoreResponse
    recommended_action: str
    trajectory: ScoreTrajectoryResponse | None = None
    dna: OpportunityDNAResponse | None = None   # new field
    evidence: list[EvidenceItemResponse] = []
```

`dna` is typed `| None` for schema backward compatibility, but in practice it will always be non-null for any opportunity with a valid `OpportunityScore`.

---

## Route changes

**File:** `src/api/routes/briefing.py`

Add a helper function (mirrors `_to_trajectory_response`):

```python
def _to_dna_response(score: OpportunityScore) -> OpportunityDNAResponse:
    dna = OpportunityDNA.from_score(score)
    return OpportunityDNAResponse(
        archetype=dna.archetype,
        archetype_description=dna.archetype_description,
        dimensions=DimensionsResponse(**dna.dimensions),
        dominant_signal=dna.dominant_signal,
    )
```

In the `OpportunityResponse` constructor call, add:

```python
dna=_to_dna_response(o.score),
```

---

## Data flow (updated)

```
ScoringEngine.score()
  → OpportunityScore (stored in Opportunity.score, persisted in DB)
  → GetBriefingUseCase returns Opportunity list
  → briefing.py route:
      ├── OpportunityScoreResponse  (existing)
      ├── ScoreTrajectoryResponse   (existing, computed at read time)
      └── OpportunityDNAResponse    (new, computed at read time via OpportunityDNA.from_score)
```

---

## File map

| File | Action | Notes |
|---|---|---|
| `src/domain/value_objects/opportunity_dna.py` | CREATE | New frozen dataclass + classification logic |
| `src/api/schemas/opportunity.py` | MODIFY | Add `DimensionsResponse`, `OpportunityDNAResponse`; update `OpportunityResponse` |
| `src/api/routes/briefing.py` | MODIFY | Import DNA types, add `_to_dna_response()`, wire into response loop |
| `tests/unit/test_opportunity_dna.py` | CREATE | Unit tests for all archetype branches and dominant_signal |

**No changes to:**
- `src/domain/entities/opportunity.py`
- `src/domain/value_objects/opportunity_score.py`
- `src/application/services/scoring_engine.py`
- Any DB migration or infrastructure file

# Spec — opportunity-dna

## Functional Requirements

### FR-1: OpportunityDNA value object

A new frozen value object `OpportunityDNA` must exist in the domain layer with the following fields:

| Field | Type | Description |
|---|---|---|
| `archetype` | `str` | Named archetype label (see FR-3) |
| `archetype_description` | `str` | One-sentence human description of the archetype |
| `dimensions` | `dict[str, float]` | All five dimension scores, keyed by canonical name |
| `dominant_signal` | `str` | Name of the dimension with the highest score |

`OpportunityDNA` must be computable from an `OpportunityScore` alone via a pure class method:

```python
@classmethod
def from_score(cls, score: OpportunityScore) -> OpportunityDNA: ...
```

No I/O, no async, no external dependencies.

---

### FR-2: dominant_signal derivation

`dominant_signal` is the key of the dimension with the highest numerical value among:
`trend_velocity`, `competition_gap`, `social_signal`, `monetization_intent`, `frustration_level`.

In case of a tie, prefer the dimension with higher weight in the default `ScoringEngine` (tie-break order: `trend_velocity` > `competition_gap` > `monetization_intent` > `social_signal` > `frustration_level`).

---

### FR-3: Archetype classification rules

Archetypes are derived from threshold comparisons on the five dimension scores (0–10 scale). Rules are evaluated in priority order — first match wins.

#### Archetype table

| Archetype | Trigger condition | Description |
|---|---|---|
| **Blue Ocean** | `competition_gap >= 7.0` AND `monetization_intent >= 7.0` | High demand, low competition, strong monetization potential |
| **Pain Point** | `frustration_level >= 7.0` AND `social_signal >= 6.5` | Clear user pain backed by strong community signal |
| **Trend Play** | `trend_velocity >= 7.5` AND `trend_velocity > competition_gap` | Fast-moving topic with momentum; competition hasn't caught up |
| **Niche Dominator** | `competition_gap >= 6.5` AND `frustration_level >= 6.0` | Underserved niche with tangible user frustration to solve |
| **Emerging** | All dimensions `>= 3.5` AND all dimensions `< 7.0` | Balanced, promising signal across all dimensions; still early |
| **Weak Signal** | *(default — none of the above matched)* | Mixed or low signals; requires more data before acting |

Rules must be pure Python — no regex, no ML, no external config file. Thresholds are constants defined in the value object module.

---

### FR-4: Backward compatibility

Every existing `Opportunity` row already has all five dimension values persisted in `OpportunityScore`. DNA is computed at API read time from those values. No DB migration, no re-running the pipeline.

---

### FR-5: API surface

`OpportunityResponse` gains a new optional field `dna: OpportunityDNAResponse | None`. It must be non-null for any opportunity that has a valid `OpportunityScore`.

The `dimensions` dict in the response must include all five dimensions, including `frustration_level` (currently absent from `OpportunityScoreResponse`).

---

## Non-Functional Requirements

### NFR-1: Performance

DNA computation must complete in under 1ms. It is pure CPU — no I/O, no DB access, no LLM calls.

### NFR-2: Immutability

`OpportunityDNA` must be a frozen dataclass (like `OpportunityScore`). Instances must not be mutated after creation.

### NFR-3: No domain coupling to infrastructure

`OpportunityDNA` must have zero imports from `infrastructure`, `api`, or `application` layers.

---

## Acceptance Scenarios

### Scenario 1 — Blue Ocean archetype
```
Given: competition_gap=8.5, monetization_intent=7.2, others=5.0
Then: archetype="Blue Ocean"
And:  dominant_signal="competition_gap"
```

### Scenario 2 — Pain Point archetype
```
Given: frustration_level=8.0, social_signal=7.0, others=4.0
Then: archetype="Pain Point"
And:  dominant_signal="frustration_level"
```

### Scenario 3 — Trend Play archetype
```
Given: trend_velocity=8.5, competition_gap=5.0, others=4.0
Then: archetype="Trend Play"
And:  dominant_signal="trend_velocity"
```

### Scenario 4 — Niche Dominator archetype
```
Given: competition_gap=7.0, frustration_level=6.5, monetization_intent=4.0, trend_velocity=4.0
Then: archetype="Niche Dominator"
And:  dominant_signal="competition_gap"
```

### Scenario 5 — Emerging archetype
```
Given: all dimensions = 5.0
Then: archetype="Emerging"
And:  dominant_signal resolves by tie-break to "trend_velocity"
```

### Scenario 6 — Weak Signal archetype (default)
```
Given: all dimensions = 2.0
Then: archetype="Weak Signal"
```

### Scenario 7 — Blue Ocean takes priority over Niche Dominator
```
Given: competition_gap=8.0, monetization_intent=7.5, frustration_level=6.5
Then: archetype="Blue Ocean" (higher-priority rule wins)
```

### Scenario 8 — API response includes dna field
```
Given: a valid briefing with N opportunities
When:  GET /briefing/{niche_id} is called
Then:  each opportunity in response has a non-null "dna" block
And:   "dna.dimensions" contains all 5 keys including "frustration_level"
```

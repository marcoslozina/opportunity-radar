# Tasks — opportunity-dna

## Phase 1 — Domain: OpportunityDNA value object

### Task 1.1 — Create `OpportunityDNA` frozen dataclass
**File:** `src/domain/value_objects/opportunity_dna.py`  
**Complexity:** Medium  
**What to implement:**
- Frozen dataclass with fields: `archetype`, `archetype_description`, `dimensions`, `dominant_signal`
- Module-level threshold constants (all 8 `_BLUE_OCEAN_*`, `_PAIN_POINT_*`, etc.)
- `_TIE_BREAK_ORDER` list for dominant_signal tie resolution
- `from_score(cls, score: OpportunityScore) -> OpportunityDNA` classmethod
- Private `_classify(dims) -> tuple[str, str]` function with priority-ordered if-chain
- Private `_dominant_signal(dims) -> str` function using tie-break order
- Full type hints + `from __future__ import annotations`

**Archetype priority order (first match wins):**
1. Blue Ocean: `competition_gap >= 7.0 AND monetization_intent >= 7.0`
2. Pain Point: `frustration_level >= 7.0 AND social_signal >= 6.5`
3. Trend Play: `trend_velocity >= 7.5 AND trend_velocity > competition_gap`
4. Niche Dominator: `competition_gap >= 6.5 AND frustration_level >= 6.0`
5. Emerging: all dims `>= 3.5 AND < 7.0`
6. Weak Signal: default fallback

**No imports from `api`, `application`, or `infrastructure`.**

---

## Phase 2 — API Schema: Response types

### Task 2.1 — Add `DimensionsResponse` and `OpportunityDNAResponse` to schemas
**File:** `src/api/schemas/opportunity.py`  
**Complexity:** Low  
**What to implement:**
- `DimensionsResponse(BaseModel)` with all 5 fields as `float` — including `frustration_level`
- `OpportunityDNAResponse(BaseModel)` with `archetype`, `archetype_description`, `dimensions: DimensionsResponse`, `dominant_signal`
- Add `dna: OpportunityDNAResponse | None = None` to `OpportunityResponse`

---

## Phase 3 — API Route: Wire DNA into briefing response

### Task 3.1 — Add `_to_dna_response` helper and wire into route
**File:** `src/api/routes/briefing.py`  
**Complexity:** Low  
**What to implement:**
- Import `OpportunityDNA` from `domain.value_objects.opportunity_dna`
- Import `DimensionsResponse`, `OpportunityDNAResponse` from `api.schemas.opportunity`
- Add `_to_dna_response(score: OpportunityScore) -> OpportunityDNAResponse` helper:
  - Calls `OpportunityDNA.from_score(score)`
  - Maps to `OpportunityDNAResponse` with `DimensionsResponse(**dna.dimensions)`
- In the `OpportunityResponse` construction inside `get_briefing`, add: `dna=_to_dna_response(o.score)`

---

## Phase 4 — Tests: Archetype classification unit tests

### Task 4.1 — Unit tests for `OpportunityDNA.from_score`
**File:** `tests/unit/test_opportunity_dna.py`  
**Complexity:** Medium  
**Minimum 8 test cases, naming: `test_<what>_when_<condition>_then_<result>`**

| Test | Scenario |
|---|---|
| `test_archetype_when_high_competition_gap_and_monetization_then_blue_ocean` | cg=8.5, mi=7.2, others=5.0 |
| `test_archetype_when_high_frustration_and_social_then_pain_point` | fl=8.0, ss=7.0, others=4.0 |
| `test_archetype_when_high_trend_velocity_and_low_competition_then_trend_play` | tv=8.5, cg=5.0, others=4.0 |
| `test_archetype_when_niche_gap_and_frustration_then_niche_dominator` | cg=7.0, fl=6.5, mi=4.0, tv=4.0 |
| `test_archetype_when_all_mid_range_then_emerging` | all dims=5.0 |
| `test_archetype_when_all_low_then_weak_signal` | all dims=2.0 |
| `test_blue_ocean_takes_priority_over_niche_dominator` | cg=8.0, mi=7.5, fl=6.5 — expect Blue Ocean |
| `test_dominant_signal_when_tie_then_resolves_by_tiebreak_order` | all dims=5.0 — expect trend_velocity |
| `test_dominant_signal_when_clear_winner` | mi=9.1, others=5.0 — expect monetization_intent |
| `test_dimensions_dict_includes_frustration_level` | any score — check "frustration_level" key in dna.dimensions |

Each test constructs an `OpportunityScore` directly (no mock, no DB), calls `OpportunityDNA.from_score()`, and asserts the expected fields.

### Task 4.2 — Integration: Verify dna field appears in briefing API response
**File:** `tests/integration/test_api_briefing.py` (extend existing file)  
**Complexity:** Low  
**What to add:**
- Assert that `response["opportunities"][0]["dna"]` is not null
- Assert that `dna["dimensions"]` contains all 5 keys
- Assert that `dna["archetype"]` is a non-empty string

---

## Dependency order

```
Task 1.1  →  Task 2.1  →  Task 3.1
                              ↓
                          Task 4.1 (can run in parallel with 3.1 once 1.1 is done)
                          Task 4.2 (after 3.1)
```

## Estimated complexity summary

| Task | Complexity | Files touched |
|---|---|---|
| 1.1 OpportunityDNA value object | Medium | 1 new file |
| 2.1 API schema additions | Low | 1 existing file |
| 3.1 Route wiring | Low | 1 existing file |
| 4.1 Unit tests | Medium | 1 new file |
| 4.2 Integration test extension | Low | 1 existing file |

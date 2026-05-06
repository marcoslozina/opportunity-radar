# Explore — opportunity-dna

## Current State

### Dimensions in `OpportunityScore` (frozen dataclass, range 0–10 each)

| Field | Meaning | Weight (default) |
|---|---|---|
| `trend_velocity` | Growth speed of the topic | 0.30 |
| `competition_gap` | Space between demand and supply | 0.25 |
| `social_signal` | Community noise / organic demand | 0.20 |
| `monetization_intent` | Explicit buying signals | 0.25 |
| `frustration_level` | User pain expressed online | 0.00 (default) |

`total` = weighted sum × 10 → range 0–100.  
`confidence` = "high" | "medium" | "low" (driven by number of signal sources).

### Name mapping (OpportunityScore → example output in prompt)

The context example uses different names (`social_demand`, `competition_gap`, `monetization_potential`, `frustration_signal`) — those are the *intended display names* for the DNA, **not** the actual field names in `OpportunityScore`. The canonical source-of-truth names are the ones in the dataclass above.

### How scores flow to the API

```
ScoringEngine.score()
  → OpportunityScore (domain value object, stored in Opportunity.score)
  → Persisted via SQLBriefingRepository
  → GetBriefingUseCase returns Opportunity list
  → briefing.py route maps each field manually to OpportunityScoreResponse (Pydantic)
  → OpportunityResponse returned in BriefingResponse
```

`frustration_level` exists in `OpportunityScore` and `ScoringEngine` but is **absent from `OpportunityScoreResponse`** — it is silently dropped in the API schema. This is a pre-existing gap.

### Scoring engine variants

Three engines exist (`ScoringEngine`, `RealEstateScoringEngine`, `ESGScoringEngine`), each with different weights. All produce the same `OpportunityScore` shape. DNA derivation must work regardless of which engine computed the score, since only the resulting numeric values are available downstream.

### No existing DNA concept

There is no archetype, fingerprint, or visual profile anywhere in the codebase. This is a greenfield addition.

---

## Key Questions

1. **Where should DNA live?** Domain value object vs. computed at API read time.
2. **Display names:** Should the DNA expose the raw field names (`trend_velocity`, etc.) or remap to friendlier names (`social_demand`, `frustration_signal`)?
3. **`frustration_level` gap:** Should the DNA spec include it in the API response even though `OpportunityScoreResponse` currently omits it?
4. **Archetype stability:** Should archetype rules be externally configurable (per-niche) or hardcoded in domain?
5. **Backward compatibility:** All existing rows have `OpportunityScore` stored — DNA must derive purely from those values with zero DB migration.

---

## Technical Findings

- `OpportunityScore` is a frozen dataclass — immutable, safe to pass anywhere without copying.
- `ScoringEngine._score_topic()` is synchronous and pure — a DNA compute function with the same profile (pure, sync, <1ms) fits naturally alongside it.
- The API route in `briefing.py` hand-maps each field. Adding `dna` requires adding: (a) a compute step somewhere, (b) a new Pydantic response schema, (c) a mapping call in the route.
- No database migration is required if DNA is computed at read time — all five dimension values are already persisted inside the JSON/column representation of `OpportunityScore`.
- The existing `OpportunityScoreResponse` omits `frustration_level` — the DNA can expose it cleanly for the first time in a dedicated `dimensions` block.

---

## Hypothesis

DNA is best modeled as a **domain value object `OpportunityDNA`** derived from `OpportunityScore` via a pure function. Computation happens in the **application or API layer** (not at scoring time), so no schema migration is needed. The archetype is determined by threshold rules applied to the five dimension values. The API surface adds an `OpportunityDNAResponse` schema and a `dna` field on `OpportunityResponse`.

# Proposal — opportunity-dna

## Intent

Add a human-readable "fingerprint" (`OpportunityDNA`) to each opportunity that surfaces:
1. The dimensional breakdown of scores (visual profile)
2. A named archetype derived from the combination of high/low dimensions
3. The single dominant signal (highest-scoring dimension)

---

## Option A — Compute DNA at scoring time (attach to Opportunity entity)

**How it works:**  
`ScoringEngine.score()` also calls `OpportunityDNA.from_score()` and stores the result on the `Opportunity` entity. The entity carries `dna: OpportunityDNA`. Persistence would need to either serialize the DNA or recompute it on load.

**Advantages:**
- DNA is always available on the entity, no coupling to the API layer.
- Conceptually clean: the entity knows its own fingerprint.

**Disadvantages:**
- Requires touching `Opportunity` (domain entity) and all persistence paths.
- DNA is a *derived* value — storing a derivation of another field violates DRY and risks inconsistency if scoring weights change.
- Forces a DB migration or a JSON column expansion to persist `dna`.
- `OpportunityDNA` would be computed every time the pipeline runs, even for consumers that never need it.
- Breaks backward compatibility for already-persisted rows (they have no DNA field).

---

## Option B — Compute DNA at read time (derive from OpportunityScore in API / application layer)

**How it works:**  
`OpportunityDNA` is a domain value object with a pure class method `from_score(score: OpportunityScore) -> OpportunityDNA`. It is instantiated inside the **briefing route** (or a thin application service helper) when building `OpportunityResponse`. No entity is modified, no DB schema changes.

**Advantages:**
- Zero DB migration — all existing rows already have the five dimension values.
- `Opportunity` entity stays clean; DNA is a derived view, not stored state.
- Pure function, trivially testable, <1ms, no I/O.
- Fully backward compatible: every historical row returns DNA on the next API call.
- The computation lives closest to where it's consumed (API response assembly), consistent with how `ScoreTrajectory` is already handled in `TrajectoryService`.

**Disadvantages:**
- DNA is recomputed on every API call (acceptable: pure CPU, ~microseconds).
- The domain entity doesn't expose DNA directly — callers must call `OpportunityDNA.from_score()` themselves.

---

## Recommendation: Option B

Compute DNA at read time.

**Reasoning:**  
DNA is a *derived view* of `OpportunityScore`, not independent state. Storing a derivative of already-persisted data would introduce redundancy and force a DB migration that provides no benefit. The existing codebase already follows this pattern: `ScoreTrajectory` is computed at read time by `TrajectoryService` from two `OpportunityScore` snapshots without touching the entity. `OpportunityDNA` fits the same contract: pure function, no I/O, computed when building the response.

The value object lives in `src/domain/value_objects/opportunity_dna.py`, keeping archetype rules in the domain where they belong semantically. Computation is invoked in `briefing.py` during response assembly, exactly where `ScoreTrajectoryResponse` is already computed.

---

## Scope

| In scope | Out of scope |
|---|---|
| `OpportunityDNA` value object + archetype rules | Storing DNA in DB |
| `OpportunityDNAResponse` Pydantic schema | Per-niche configurable archetype rules |
| `dna` field on `OpportunityResponse` | Dashboard / frontend rendering |
| Unit tests for all archetype branches | Archetype i18n / localization |
| Expose `frustration_level` in the DNA `dimensions` block | Fixing the gap in `OpportunityScoreResponse` |

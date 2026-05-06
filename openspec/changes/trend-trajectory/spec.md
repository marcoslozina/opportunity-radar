# Spec: Trend Trajectory

## Goal

Enrich each opportunity in the briefing response with a trajectory snapshot (delta, percentage change, direction label) computed by comparing the current briefing against the most recent previous briefing for the same niche.

---

## Requirements

### Functional

- **FR-1**: Each opportunity in the `GET /briefing/{niche_id}` response includes a `trajectory` field with `delta`, `delta_pct`, `direction`, `previous_total`, and `compared_at`.
- **FR-2**: Trajectory compares `score.total` of the current briefing against `score.total` of the same topic in the most recent previous briefing for the same niche (i.e., the second-latest `BriefingModel` row ordered by `generated_at DESC`).
- **FR-3**: Topic identity across briefings is resolved by `topic.lower().strip()` exact match. No semantic matching in V1.
- **FR-4**: Direction labels follow fixed thresholds applied to `delta_pct`:
  - `delta_pct >= +5%` → `"GROWING ↑"`
  - `delta_pct <= -5%` → `"COOLING ↓"`
  - `-5% < delta_pct < +5%` → `"STABLE →"`
  - No previous briefing for the niche, or topic not found in previous briefing → `"NEW"`
- **FR-5**: `trajectory` is `null` in the API response when there is no previous briefing for the niche, or when the topic does not appear in the previous briefing.
- **FR-6**: Trajectory computation is additive and non-breaking — existing `OpportunityResponse` fields (`id`, `topic`, `score`, `recommended_action`) are unchanged.
- **FR-7**: The index migration on `briefings(niche_id, generated_at)` is applied as a standalone additive Alembic migration (no destructive changes to existing tables or data).

### Non-Functional

- **NFR-1**: Trajectory computation adds less than 50ms to the `GET /briefing/{niche_id}` response time (one extra index-backed SQL query + in-memory join over at most ~20 topics per briefing).
- **NFR-2**: The feature degrades gracefully — if `get_previous()` raises an unexpected exception, the use case catches it, logs a warning, and returns the briefing without trajectory data rather than propagating a 500.
- **NFR-3**: No new tables introduced. The `opportunities` and `briefings` tables are not structurally changed.
- **NFR-4**: `ScoreTrajectory` is a pure frozen dataclass — no I/O, no external dependencies. All direction logic lives in a single `compute()` factory method for full testability.

---

## Scenarios (Given / When / Then)

### Scenario 1: Topic exists in both briefings — growing

Given a niche with two briefings for "Real Estate Argentina"  
And the previous briefing contains topic "Departamentos zona norte" with `total = 5.1`, `generated_at = 2026-04-28T08:00:00`  
When the current briefing contains the same topic with `total = 7.2`  
Then `trajectory.delta = +2.1`  
And `trajectory.delta_pct = +41.18` (rounded to 2 decimal places)  
And `trajectory.direction = "GROWING ↑"`  
And `trajectory.previous_total = 5.1`  
And `trajectory.compared_at = "2026-04-28T08:00:00"`

### Scenario 2: Topic exists in both briefings — cooling

Given two briefings for the same niche  
And the previous briefing contains topic "Casas en Palermo" with `total = 8.0`  
When the current briefing contains the same topic with `total = 6.5`  
Then `trajectory.delta = -1.5`  
And `trajectory.delta_pct = -18.75`  
And `trajectory.direction = "COOLING ↓"`

### Scenario 3: Topic exists in both briefings — stable

Given two briefings for the same niche  
And the previous briefing contains topic "Alquileres temporarios" with `total = 6.0`  
When the current briefing contains the same topic with `total = 6.2`  
Then `trajectory.delta = +0.2`  
And `trajectory.delta_pct = +3.33`  
And `trajectory.direction = "STABLE →"`

### Scenario 4: No previous briefing (first run for the niche)

Given a niche with exactly one briefing  
When `GET /briefing/{niche_id}` is called  
Then every opportunity has `trajectory = null`

### Scenario 5: Topic exists in current briefing but not in previous

Given two briefings for the same niche  
And the previous briefing does not contain a topic matching "Nueva oportunidad emergente"  
When the current briefing contains that topic  
Then `trajectory = null` for that opportunity  
(Client interprets `null` as direction `"NEW"` if desired — the API returns `null`, not a `"NEW"` object)

### Scenario 6: Topic matching is case-insensitive

Given previous briefing contains topic `"  Crédito Hipotecario  "` (leading/trailing spaces, mixed case)  
And current briefing contains topic `"crédito hipotecario"`  
Then they are matched via `lower().strip()` and trajectory is computed  
(No match is lost due to casing or padding alone)

### Scenario 7: Score unchanged (within stable band)

Given previous `total = 7.0` and current `total = 7.2`  
Then `delta_pct = +2.86%`, which falls within `(-5%, +5%)`  
And `direction = "STABLE →"`

---

## Out of Scope

- Per-dimension trajectory (only `total` delta in V1 — not `trend_velocity`, `competition_gap`, etc.)
- Dedicated trajectory endpoint (`GET /niches/{niche_id}/trajectory`) — trajectory lives inside the briefing response only
- Retention or pruning of historical briefings
- Topic normalization beyond `lower().strip()` — no semantic matching, slug catalog, or embedding-based identity
- Dashboard / Streamlit visualization of trajectory trends
- Historical charts or rolling averages over N weeks
- Daily granularity (requires daily pipeline runs)
- Trajectory for `ProductBriefing` / `ProductOpportunity` (different domain, different scope)

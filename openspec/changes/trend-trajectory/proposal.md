# Proposal: Trend Trajectory

## Context

The pipeline already produces a new `Briefing` with a full `OpportunityScore` snapshot every time it runs. Users currently see only the latest snapshot — there is no indication of whether a niche is heating up or cooling down. Adding trajectory (e.g., "score 7.2 today vs 5.1 seven days ago → GROWING +41%") transforms the briefing from a static scorecard into a signal for prioritization decisions.

---

## Option A — Compute at Read Time (Query-Based Trajectory)

**How it works:**

The existing `opportunities` rows already encode history implicitly through `BriefingModel.generated_at`. A new `get_previous()` method is added to `BriefingRepository`, fetching the second-most-recent briefing for a niche. The application layer (new `GetTrajectoryUseCase` or enriched `GetBriefingUseCase`) joins both briefings in memory, matches topics by normalized string (`lower().strip()`), computes a `ScoreTrajectory` value object per matched pair, and attaches it to the `OpportunityResponse` in the API schema. No new tables. One additive migration to add a `btree` index on `briefings(niche_id, generated_at)` for fast double-fetch queries.

**Domain model additions:**
```
domain/value_objects/score_trajectory.py
  ScoreTrajectory(frozen=True)
    previous_total: float
    delta: float           # total_now - total_prev
    delta_pct: float       # (delta / previous_total) * 100
    direction: str         # "GROWING" | "STABLE" | "COOLING"
    compared_at: datetime
```

**`direction` thresholds (configurable):**
- `delta_pct >= +5%` → `GROWING`
- `delta_pct <= -5%` → `COOLING`
- otherwise → `STABLE`

**`Opportunity` entity stays unchanged.** Trajectory is a read-model concern computed in the application layer and surfaced only in the API response schema.

**`BriefingRepository` port gains:**
```python
@abstractmethod
async def get_previous(self, niche_id: NicheId) -> Briefing | None: ...
```

**API response enrichment (additive, non-breaking):**
```json
{
  "id": "...",
  "topic": "crédito hipotecario Argentina",
  "score": { "total": 7.2, ... },
  "trajectory": {
    "previous_total": 5.1,
    "delta": 2.1,
    "delta_pct": 41.2,
    "direction": "GROWING",
    "compared_at": "2026-04-28T08:00:00"
  }
}
```

`trajectory` is `null` when there is no previous briefing (first run for a niche, or topic is new).

**Advantages:**
- Zero schema changes to existing tables — fully backwards-compatible.
- No data duplication — reuses the history that already accumulates.
- Simple to reason about: two SQL queries, one in-memory join.
- Reversible: remove the application logic and the index, done.
- Works immediately with existing data in production.

**Disadvantages:**
- Topic matching by string is fragile for LLM-generated text (minor paraphrasing breaks the link). Mitigated by `lower().strip()` normalization for V1.
- Two queries per API call instead of one (both small, index-backed — negligible at current scale).
- If topic strings drift significantly across runs (e.g., "UVA 2025" vs "crédito UVA"), the trajectory appears as `null` rather than incorrect — a silent miss, not a wrong answer.

**Best when:** The dataset is small-to-medium, the pipeline runs infrequently (weekly), and topic strings are reasonably stable across runs. This is the current state of the project.

---

## Option B — Dedicated `ScoreHistoryModel` Table

**How it works:**

A new `score_history` table is created, storing one row per `(niche_id, normalized_topic, recorded_at)` with the full score snapshot. After each pipeline run, `RunPipelineUseCase` writes history rows in addition to the briefing. Trajectory is computed by querying the two most recent history rows for each topic. A domain `ScoreHistoryRepository` port is introduced alongside the existing `BriefingRepository`.

**New schema:**
```sql
CREATE TABLE score_history (
  id          VARCHAR(36) PRIMARY KEY,
  niche_id    VARCHAR(36) NOT NULL REFERENCES niches(id) ON DELETE CASCADE,
  topic       VARCHAR(500) NOT NULL,
  total       FLOAT NOT NULL,
  recorded_at DATETIME NOT NULL,
  INDEX (niche_id, topic, recorded_at)
);
```

**Advantages:**
- Clean, purpose-built table — trajectory queries are a single scan without joining through briefings.
- Enables per-topic time-series analytics in future (charts, rolling averages, anomaly detection).
- Easy to apply a retention policy independently of briefings (e.g., purge rows older than 90 days without touching briefings).
- Topic normalization is applied once at write time — consistent identity across all downstream queries.

**Disadvantages:**
- New table, new port, new repository, new migration — significantly more surface area.
- Data duplication: score data already lives in `opportunities`; now it also lives in `score_history`.
- `RunPipelineUseCase` gains a second write dependency, making it harder to test and reason about atomicity (two separate `commit()` calls or a coordinated transaction).
- Backfill required: existing historical `opportunities` data is not automatically available in `score_history`.
- Overkill for the current scale: weekly pipeline, handful of niches.

**Best when:** The pipeline runs multiple times per day, there are dozens of niches, topic identity is managed explicitly (e.g., slug normalization or a topics catalog table), and time-series visualization is a near-term roadmap item.

---

## Recommended Option

**Option A — Compute at Read Time.**

The project is in its growth phase: a small number of niches, weekly pipeline runs, SQLite in development, no existing time-series query patterns. Option A delivers the full trajectory UX (delta, percentage, direction label, `compared_at`) with no schema changes to the core tables, zero data duplication, and immediate compatibility with existing production data. The only addition is an index migration, a value object, a repository method, a use case enrichment, and a schema field.

Option B is the right answer in six months if the feature proves valuable and the pipeline moves to daily runs — at that point, migrating from Option A to B is a straightforward backfill + swap, because the trajectory value object and API contract defined in Option A will remain unchanged.

---

## Scope

**In scope:**
- `ScoreTrajectory` value object in the domain layer
- `get_previous()` method on `BriefingRepository` port and `SQLBriefingRepository` implementation
- Trajectory computation logic in the application layer (new `ComputeTrajectoryService` or inline in `GetBriefingUseCase`)
- Enriched `OpportunityResponse` and `BriefingResponse` schemas (additive — `trajectory: ScoreTrajectoryResponse | None`)
- Updated `GET /briefing/{niche_id}` route to include trajectory
- One Alembic migration: `CREATE INDEX ix_briefings_niche_generated ON briefings(niche_id, generated_at)`
- Unit tests for `ScoreTrajectory` logic and direction thresholds
- Integration test: two pipeline runs → trajectory appears in briefing response

**Out of scope:**
- Per-dimension trajectory (only `total` delta for V1)
- Dedicated trajectory endpoint (trajectory lives inside the briefing response)
- Retention/pruning logic (existing briefings are retained indefinitely in V1)
- Topic normalization beyond `lower().strip()` (no semantic matching, no slug catalog)
- Dashboard visualization (Streamlit changes)
- Historical charts or rolling averages

---

## Affected Files (estimated)

| File | Change type |
|---|---|
| `src/domain/value_objects/score_trajectory.py` | **New** — `ScoreTrajectory` frozen dataclass |
| `src/domain/ports/repository_ports.py` | **Modify** — add `get_previous()` abstract method to `BriefingRepository` |
| `src/infrastructure/db/repositories.py` | **Modify** — implement `get_previous()` in `SQLBriefingRepository` |
| `src/application/services/trajectory_service.py` | **New** — `TrajectoryService.compute(current, previous)` returns `dict[str, ScoreTrajectory]` |
| `src/application/use_cases/get_briefing.py` | **Modify** — inject `TrajectoryService`, return enriched result |
| `src/api/schemas/opportunity.py` | **Modify** — add `ScoreTrajectoryResponse`, `trajectory: ScoreTrajectoryResponse \| None` to `OpportunityResponse` |
| `src/api/routes/briefing.py` | **Modify** — map trajectory onto response |
| `alembic/versions/<new_revision>.py` | **New** — index on `briefings(niche_id, generated_at)` |
| `tests/unit/test_trajectory_service.py` | **New** — unit tests for delta/pct/direction logic |
| `tests/integration/test_trajectory_api.py` | **New** — two-run scenario, verify `direction` and `delta_pct` in response |

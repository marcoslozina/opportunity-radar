# Tasks: Trend Trajectory

## Phase 1 — Domain

- [ ] **1.1** Create `src/domain/value_objects/score_trajectory.py`
  - Frozen dataclass `ScoreTrajectory` with fields: `previous_total: float`, `delta: float`, `delta_pct: float`, `direction: str`, `compared_at: datetime`
  - Class method `ScoreTrajectory.compute(current_total, previous_total, compared_at) -> ScoreTrajectory`
  - Direction thresholds: `>= 5%` → `"GROWING ↑"`, `<= -5%` → `"COOLING ↓"`, otherwise `"STABLE →"`
  - Division-by-zero guard: if `previous_total == 0`, `delta_pct = 0.0`
  - `from __future__ import annotations`, full type hints, no external imports

---

## Phase 2 — Infrastructure

- [ ] **2.1** Add `get_previous()` abstract method to `BriefingRepository` port
  - File: `src/domain/ports/repository_ports.py`
  - Signature: `async def get_previous(self, niche_id: NicheId) -> Briefing | None: ...`
  - Docstring: "Returns the second-most-recent Briefing for the niche, or None if fewer than 2 exist."

- [ ] **2.2** Implement `get_previous()` in `SQLBriefingRepository`
  - File: `src/infrastructure/db/repositories.py`
  - Query: `select(BriefingModel).options(selectinload(BriefingModel.opportunities)).where(niche_id==...).order_by(generated_at.desc()).offset(1).limit(1)`
  - Return `_to_briefing(result) if result else None`

- [ ] **2.3** Create Alembic migration: composite index on `briefings(niche_id, generated_at)`
  - File: `alembic/versions/<new_revision>.py` (generate with `alembic revision --autogenerate -m "add ix_briefings_niche_generated"` and clean up)
  - `upgrade()`: `op.create_index("ix_briefings_niche_generated", "briefings", ["niche_id", "generated_at"])`
  - `downgrade()`: `op.drop_index("ix_briefings_niche_generated", table_name="briefings")`

---

## Phase 3 — Application

- [ ] **3.1** Create `src/application/services/trajectory_service.py`
  - Class `TrajectoryService` (plain, no ABC)
  - Method `compute(current: Briefing, previous: Briefing | None) -> dict[str, ScoreTrajectory]`
  - Build `previous_index: dict[str, float]` via `{opp.topic.lower().strip(): opp.score.total for opp in previous.opportunities}`
  - For each opportunity in `current`, look up normalized key; call `ScoreTrajectory.compute()` if found
  - Return `{}` immediately if `previous is None`

- [ ] **3.2** Update `GetBriefingUseCase`
  - File: `src/application/use_cases/get_briefing.py`
  - Inject `trajectory_service: TrajectoryService` via `__init__`
  - Change return type to `tuple[Briefing, dict[str, ScoreTrajectory]] | None`
  - After loading `current`, call `get_previous()` wrapped in `try/except Exception` (degrade to `None` on error)
  - Call `trajectory_service.compute(current, previous)` and return `(current, trajectory_map)`

---

## Phase 4 — API

- [ ] **4.1** Add `ScoreTrajectoryResponse` schema
  - File: `src/api/schemas/opportunity.py`
  - Pydantic `BaseModel` with fields: `previous_total: float`, `delta: float`, `delta_pct: float`, `direction: str`, `compared_at: datetime`

- [ ] **4.2** Add `trajectory: ScoreTrajectoryResponse | None = None` field to `OpportunityResponse`
  - File: `src/api/schemas/opportunity.py`
  - Default is `None` — additive, non-breaking for existing clients

- [ ] **4.3** Update `briefing` route to unpack use case result and map trajectory
  - File: `src/api/routes/briefing.py`
  - Unpack `(briefing, trajectory_map) = result`
  - For each opportunity, call `trajectory_map.get(opp.topic.lower().strip())` and map to `ScoreTrajectoryResponse`
  - Add private helper `_to_trajectory_response(t: ScoreTrajectory | None) -> ScoreTrajectoryResponse | None`

- [ ] **4.4** Update DI wiring to inject `TrajectoryService` into `GetBriefingUseCase`
  - Locate the app factory / dependency injection site (likely `src/api/dependencies.py` or `main.py`)
  - Instantiate `TrajectoryService()` (stateless — one instance) and pass to use case constructor

---

## Phase 5 — Tests

- [ ] **5.1** Unit tests for `ScoreTrajectory.compute()`
  - File: `tests/unit/test_score_trajectory.py`
  - `test_compute_when_score_grows_then_direction_is_growing` — delta_pct >= 5%
  - `test_compute_when_score_cools_then_direction_is_cooling` — delta_pct <= -5%
  - `test_compute_when_score_stable_then_direction_is_stable` — delta_pct in (-5%, 5%)
  - `test_compute_when_previous_total_is_zero_then_delta_pct_is_zero`
  - `test_compute_delta_and_delta_pct_are_rounded_to_2_decimal_places`

- [ ] **5.2** Unit tests for `TrajectoryService.compute()`
  - File: `tests/unit/test_trajectory_service.py`
  - `test_compute_when_previous_is_none_then_returns_empty_dict`
  - `test_compute_when_topic_matches_then_trajectory_is_computed`
  - `test_compute_when_topic_missing_in_previous_then_key_absent`
  - `test_compute_topic_matching_is_case_insensitive_and_strips_whitespace`
  - Use `Briefing` factory helpers (build minimal `Opportunity` / `Briefing` objects in-memory — no DB)

- [ ] **5.3** Unit test for `GetBriefingUseCase` with trajectory
  - File: `tests/unit/test_get_briefing.py` (or extend existing)
  - Fake `BriefingRepository` returning controlled current + previous briefings
  - Assert returned tuple contains expected `ScoreTrajectory` for matched topic
  - Assert trajectory is absent (empty dict) when `get_previous()` returns `None`
  - Assert graceful degradation: if `get_previous()` raises, use case returns `(current, {})`

- [ ] **5.4** Integration test: two pipeline runs produce trajectory in briefing response
  - File: `tests/integration/test_trajectory_api.py`
  - Setup: insert two `BriefingModel` rows for the same niche with overlapping topics and different scores
  - Call `GET /briefing/{niche_id}` via test client
  - Assert response status 200
  - Assert at least one opportunity has `trajectory.direction` in `["GROWING ↑", "COOLING ↓", "STABLE →"]`
  - Assert `trajectory.compared_at` matches the previous briefing's `generated_at`
  - Assert an opportunity with no prior match has `trajectory = null`

---

## Execution Order (dependencies)

```
1.1 (ScoreTrajectory VO)
  └─► 3.1 (TrajectoryService)
        └─► 3.2 (GetBriefingUseCase update)
              └─► 4.3, 4.4 (route + DI)

2.1 (port get_previous)
  └─► 2.2 (SQL impl)
        └─► 3.2

2.3 (migration) — independent, can run in parallel with any phase

4.1, 4.2 (schemas) — independent, can run before or in parallel with 4.3

5.x — after all implementation phases complete
```

Phases 1, 2.3, and 4.1/4.2 have no inter-dependencies and can be implemented in parallel.

# Design: Trend Trajectory

## Architecture Overview

```
GET /briefing/{niche_id}
        │
        ▼
GetBriefingUseCase.execute(niche_id)
        │
        ├─► BriefingRepository.get_latest(niche_id)   → Briefing (current)
        │
        ├─► BriefingRepository.get_previous(niche_id) → Briefing | None (previous)
        │
        └─► TrajectoryService.compute(current, previous)
                │  matches topics by lower().strip()
                │  creates ScoreTrajectory per matched pair
                │
                ▼
        dict[normalized_topic, ScoreTrajectory]
                │
                ▼ attach to OpportunityResponse
        BriefingResponse (enriched, non-breaking)
```

The enrichment happens entirely in the **application layer**. The domain entity `Opportunity` is not modified — trajectory is a read-model concern surfaced only in API response schemas.

---

## Domain Layer Changes

### New Value Object — `ScoreTrajectory`

**File:** `src/domain/value_objects/score_trajectory.py`

```python
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ScoreTrajectory:
    previous_total: float
    delta: float          # current_total - previous_total
    delta_pct: float      # (delta / previous_total) * 100, rounded to 2dp
    direction: str        # "GROWING ↑" | "COOLING ↓" | "STABLE →"
    compared_at: datetime

    @classmethod
    def compute(
        cls,
        current_total: float,
        previous_total: float,
        compared_at: datetime,
    ) -> ScoreTrajectory:
        delta = round(current_total - previous_total, 2)
        delta_pct = round((delta / previous_total) * 100, 2) if previous_total != 0 else 0.0
        if delta_pct >= 5.0:
            direction = "GROWING ↑"
        elif delta_pct <= -5.0:
            direction = "COOLING ↓"
        else:
            direction = "STABLE →"
        return cls(
            previous_total=previous_total,
            delta=delta,
            delta_pct=delta_pct,
            direction=direction,
            compared_at=compared_at,
        )
```

**Design decisions:**
- `frozen=True` — value object, identity by value.
- `previous_total` and `compared_at` are included so the API client can render "was X on date Y" without a second call.
- Direction threshold is `>= 5%` / `<= -5%`. The `5%` constant is defined inline in `compute()` for V1; it can be moved to `Settings` if configurability is needed later.
- Division-by-zero guard: if `previous_total == 0`, `delta_pct = 0.0` and direction resolves to `"STABLE →"`. This edge case is unlikely (scores are 0–100 and LLM-generated) but safe.
- The `"NEW"` state is NOT encoded in `ScoreTrajectory` — it is represented by `trajectory = None` at the application/API layer. This keeps the value object's invariant clean: a `ScoreTrajectory` always has a valid comparison pair.

### `Opportunity` entity — NO CHANGES

Trajectory is deliberately kept out of the domain entity. `Opportunity` represents a point-in-time signal snapshot; trajectory is a derived comparison across two snapshots. Placing trajectory in the entity would couple the domain to historical query semantics.

---

## Infrastructure Layer Changes

### `BriefingRepository` port — add `get_previous()`

**File:** `src/domain/ports/repository_ports.py`

Add one abstract method to `BriefingRepository`:

```python
@abstractmethod
async def get_previous(self, niche_id: NicheId) -> Briefing | None: ...
```

**Contract:** Returns the second-most-recent `Briefing` for the given `niche_id` (ordered by `generated_at DESC`, offset 1), including all its `Opportunity` objects. Returns `None` if fewer than two briefings exist for the niche.

### `SQLBriefingRepository` — implement `get_previous()`

**File:** `src/infrastructure/db/repositories.py`

```python
async def get_previous(self, niche_id: NicheId) -> Briefing | None:
    stmt = (
        select(BriefingModel)
        .options(selectinload(BriefingModel.opportunities))
        .where(BriefingModel.niche_id == str(niche_id))
        .order_by(BriefingModel.generated_at.desc())
        .offset(1)
        .limit(1)
    )
    result = await self._session.scalar(stmt)
    return _to_briefing(result) if result else None
```

**Why `.offset(1).limit(1)`:** SQLAlchemy async with `selectinload` does not support `LIMIT/OFFSET` at the subquery level when using joined loading, but the pattern is correct for the top-level `BriefingModel` query. The `selectinload` fetches opportunities in a separate IN query — safe and efficient.

### Alembic Migration — index on `briefings(niche_id, generated_at)`

**File:** `alembic/versions/<new_revision>.py`

```python
def upgrade() -> None:
    op.create_index(
        "ix_briefings_niche_generated",
        "briefings",
        ["niche_id", "generated_at"],
    )

def downgrade() -> None:
    op.drop_index("ix_briefings_niche_generated", table_name="briefings")
```

**Why this index:** Both `get_latest()` and `get_previous()` filter by `niche_id` and order by `generated_at DESC`. Without the composite index, each call does a full table scan over `briefings`. With the index, both queries resolve in O(log N). The index is additive — no data changes, no locking in SQLite, minimal impact in PostgreSQL.

**Note on sort direction:** SQLite and PostgreSQL both use the ascending index for `DESC` queries efficiently. No need for a DESC index in V1.

---

## Application Layer Changes

### New Service — `TrajectoryService`

**File:** `src/application/services/trajectory_service.py`

```python
from __future__ import annotations
from domain.entities.briefing import Briefing
from domain.value_objects.score_trajectory import ScoreTrajectory


class TrajectoryService:
    def compute(
        self,
        current: Briefing,
        previous: Briefing | None,
    ) -> dict[str, ScoreTrajectory]:
        """
        Returns a mapping of normalized_topic → ScoreTrajectory.
        Only topics present in BOTH briefings are included.
        Topics with no match in `previous` are absent from the result
        (caller treats missing key as trajectory=None).
        """
        if previous is None:
            return {}

        previous_index: dict[str, tuple[float, ...]] = {
            opp.topic.lower().strip(): (opp.score.total,)
            for opp in previous.opportunities
        }

        result: dict[str, ScoreTrajectory] = {}
        for opp in current.opportunities:
            key = opp.topic.lower().strip()
            if key in previous_index:
                prev_total = previous_index[key][0]
                result[key] = ScoreTrajectory.compute(
                    current_total=opp.score.total,
                    previous_total=prev_total,
                    compared_at=previous.generated_at,
                )
        return result
```

**Design decisions:**
- `TrajectoryService` is a plain class (no ABC needed — there is only one implementation). It is injected into `GetBriefingUseCase` via constructor.
- The `previous_index` dict is built once per call — O(N) space, O(1) lookup per current opportunity. Total cost: O(N + M) where N = previous opportunities, M = current opportunities. Negligible at ~20 topics per briefing.
- The service does not raise — it returns `{}` on any `None` input. The use case controls error handling.

### `GetBriefingUseCase` — inject and call `TrajectoryService`

**File:** `src/application/use_cases/get_briefing.py`

Updated signature and flow:

```python
class GetBriefingUseCase:
    def __init__(
        self,
        repo: BriefingRepository,
        trajectory_service: TrajectoryService,
    ) -> None:
        self._repo = repo
        self._trajectory_service = trajectory_service

    async def execute(
        self, niche_id: NicheId
    ) -> tuple[Briefing, dict[str, ScoreTrajectory]] | None:
        current = await self._repo.get_latest(niche_id)
        if current is None:
            return None
        try:
            previous = await self._repo.get_previous(niche_id)
        except Exception:
            previous = None  # degrade gracefully — log warning in production
        trajectory_map = self._trajectory_service.compute(current, previous)
        return current, trajectory_map
```

**Return type change:** The use case now returns `(Briefing, dict[str, ScoreTrajectory]) | None` instead of `Briefing | None`. The API route unpacks the tuple and maps trajectory onto each `OpportunityResponse` by normalized topic key.

**Graceful degradation:** If `get_previous()` raises (e.g., DB timeout), the exception is caught, `previous` defaults to `None`, and the briefing is returned without trajectory. A production system would log at WARNING level here.

---

## API Layer Changes

### New Schema — `ScoreTrajectoryResponse`

**File:** `src/api/schemas/opportunity.py`

```python
from datetime import datetime

class ScoreTrajectoryResponse(BaseModel):
    previous_total: float
    delta: float
    delta_pct: float
    direction: str
    compared_at: datetime
```

### Updated `OpportunityResponse`

```python
class OpportunityResponse(BaseModel):
    id: str
    topic: str
    score: OpportunityScoreResponse
    recommended_action: str
    trajectory: ScoreTrajectoryResponse | None = None  # additive, non-breaking
```

`trajectory` defaults to `None` — existing API clients that do not read this field are unaffected.

### Route change — `src/api/routes/briefing.py`

The route unpacks the use case's tuple result and maps the trajectory dict:

```python
result = await use_case.execute(niche_id)
if result is None:
    raise HTTPException(status_code=404)
briefing, trajectory_map = result

opportunities = [
    OpportunityResponse(
        id=str(opp.id),
        topic=opp.topic,
        score=...,
        recommended_action=opp.recommended_action,
        trajectory=_to_trajectory_response(
            trajectory_map.get(opp.topic.lower().strip())
        ),
    )
    for opp in briefing.top_10
]
```

`_to_trajectory_response()` is a private mapper that converts `ScoreTrajectory | None → ScoreTrajectoryResponse | None`.

---

## Dependency Injection

`TrajectoryService` has no external dependencies — it is instantiated directly:

```python
# In the DI wiring (e.g., api/dependencies.py or app factory)
trajectory_service = TrajectoryService()
repo = SQLBriefingRepository(session)
use_case = GetBriefingUseCase(repo=repo, trajectory_service=trajectory_service)
```

`TrajectoryService` is stateless — one instance can be shared across requests.

---

## Data Flow Diagram (summary)

```
DB: briefings table
  niche_id=X, generated_at=2026-05-05  ← get_latest()   → current Briefing
  niche_id=X, generated_at=2026-04-28  ← get_previous() → previous Briefing

TrajectoryService.compute(current, previous)
  previous_index = {"departamentos zona norte": (5.1,), ...}
  For "Departamentos zona norte" in current (total=7.2):
    key = "departamentos zona norte" → match found
    ScoreTrajectory.compute(7.2, 5.1, 2026-04-28T08:00:00)
      delta = 2.1, delta_pct = 41.18, direction = "GROWING ↑"

API response:
  { "topic": "Departamentos zona norte",
    "trajectory": { "delta": 2.1, "delta_pct": 41.18,
                    "direction": "GROWING ↑", "previous_total": 5.1,
                    "compared_at": "2026-04-28T08:00:00" } }
```

# Design: Evidence Panel

## Architecture Overview

```
Adapter._collect_evidence(raw_response)
    → list[EvidenceItem]           # collected alongside signals, same HTTP call
         │
         ▼
RunPipelineUseCase._collect_all_with_evidence()
    → (list[TrendSignal], list[EvidenceItem])
         │
         ├── signals ──► ScoringEngine.score()     [unchanged]
         │                    │
         │               dict[topic, OpportunityScore]
         │
         └── evidence ──► _build_evidence_registry()
                              top-5 per signal_type, max 15 per topic
                                   │
                                   ▼
                         Opportunity.evidence = list[EvidenceItem]
                                   │
                                   ▼
                         SQLBriefingRepository.save()
                              OpportunityModel.evidence_json = json.dumps(...)
                                   │
                                   ▼
                         GET /briefing/{niche_id}
                              OpportunityResponse.evidence = list[EvidenceItemResponse]
```

Key invariant: `TrendDataPort.collect()` is never modified. Evidence flows through
a parallel channel that does not touch the scoring pipeline.

---

## Domain Layer Changes

### New Value Object: `EvidenceItem`

**Location:** `src/domain/value_objects/evidence_item.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class EvidenceItem:
    source: str             # "reddit" | "hacker_news" | "serp" | "youtube"
    signal_type: str        # mirrors TrendSignal.signal_type
    topic: str              # same keyword that produced the signal
    title: str              # human-readable label for the evidence item
    url: str | None         # direct link to the source item; None for numeric signals
    engagement_count: int   # upvotes, points, search rank, etc.
    engagement_label: str   # "upvotes" | "points" | "rank" | "ad_position" | "search_rank"
    collected_at: datetime
```

Rationale for `frozen=True`: value objects are immutable by convention (see skill). No
`__post_init__` validation needed at this stage — adapters are trusted internal producers.

### `Opportunity` Entity Change

**File:** `src/domain/entities/opportunity.py`

Add one field with a default so `Opportunity.create()` requires no change:

```python
from domain.value_objects.evidence_item import EvidenceItem

@dataclass
class Opportunity:
    id: OpportunityId
    topic: str
    score: OpportunityScore
    recommended_action: str = field(default="")
    domain_applicability: str = field(default="")
    domain_reasoning: str = field(default="")
    evidence: list[EvidenceItem] = field(default_factory=list)  # NEW
```

The `default_factory=list` ensures old code paths that call `Opportunity.create()` continue
to work without changes — evidence starts empty and is filled by the use case.

---

## Infrastructure Layer Changes

### Adapter Changes — internal only, port contract unchanged

Each opted-in adapter gains a private `_collect_evidence()` method. The public
`collect()` method is not changed. The adapter calls `_collect_evidence()` internally
while processing the same raw response it already fetches, then stores the result in
an instance variable `_last_evidence: list[EvidenceItem]` that the use case reads after
calling `collect()`.

**Why instance variable instead of a second port method?**
The port must stay unchanged (FR-9). A second optional port (`EvidencePort`) would force
all adapters to implement it. An instance variable is the minimal non-breaking mechanism:
the use case checks `hasattr(collector, '_last_evidence')` and reads it when present.

#### `reddit.py`

```python
def _fetch(self, keyword: str) -> list[TrendSignal]:
    results = list(self._reddit.subreddit("all").search(keyword, limit=25, time_filter="week"))
    if not results:
        self._last_evidence = []
        return []
    # ... existing signal logic unchanged ...
    self._last_evidence = self._collect_evidence(keyword, results)
    return [TrendSignal(...)]

def _collect_evidence(self, keyword: str, posts: list) -> list[EvidenceItem]:
    now = datetime.now(tz=timezone.utc)
    items = [
        EvidenceItem(
            source="reddit",
            signal_type="social_signal",
            topic=keyword,
            title=post.title,
            url=f"https://reddit.com{post.permalink}",
            engagement_count=post.score,
            engagement_label="upvotes",
            collected_at=now,
        )
        for post in posts
        if post.title and post.score > 0
    ]
    return sorted(items, key=lambda e: e.engagement_count, reverse=True)[:5]
```

#### `hacker_news.py`

```python
def _collect_evidence(self, keyword: str, hits: list[dict]) -> list[EvidenceItem]:
    now = datetime.now(tz=timezone.utc)
    items = [
        EvidenceItem(
            source="hacker_news",
            signal_type="social_signal",
            topic=keyword,
            title=hit.get("title", ""),
            url=hit.get("url"),                    # may be None for Ask HN posts
            engagement_count=hit.get("points", 0),
            engagement_label="points",
            collected_at=now,
        )
        for hit in hits
        if hit.get("title") and hit.get("points", 0) > 0
    ]
    return sorted(items, key=lambda e: e.engagement_count, reverse=True)[:5]
```

#### `serp.py`

Two evidence streams from the same response — organic results (competition_gap) and ads
(monetization_intent):

```python
def _collect_evidence(self, keyword: str, results: dict) -> list[EvidenceItem]:
    now = datetime.now(tz=timezone.utc)
    evidence: list[EvidenceItem] = []

    organic = results.get("organic_results", [])
    for i, result in enumerate(organic[:5]):
        evidence.append(EvidenceItem(
            source="serp",
            signal_type="competition_gap",
            topic=keyword,
            title=result.get("title", ""),
            url=result.get("link"),
            engagement_count=max(10 - i, 1),   # rank inverted: position 0 → count 10
            engagement_label="rank",
            collected_at=now,
        ))

    ads = results.get("ads", [])
    for i, ad in enumerate(ads[:5]):
        evidence.append(EvidenceItem(
            source="serp",
            signal_type="monetization_intent",
            topic=keyword,
            title=ad.get("title", ""),
            url=ad.get("link"),
            engagement_count=max(5 - i, 1),    # ad position inverted
            engagement_label="ad_position",
            collected_at=now,
        ))

    return evidence
```

#### `youtube.py`

YouTube search API (`part="snippet"`) does not return view counts — the adapter uses
result rank as engagement proxy. A future task can add a `videos.list` call with
`part="statistics"` to get real view counts if needed.

```python
def _collect_evidence(self, keyword: str, items: list[dict]) -> list[EvidenceItem]:
    now = datetime.now(tz=timezone.utc)
    return [
        EvidenceItem(
            source="youtube",
            signal_type="social_signal",
            topic=keyword,
            title=item["snippet"]["title"],
            url=f"https://youtube.com/watch?v={item['id']['videoId']}",
            engagement_count=max(len(items) - i, 1),  # rank: first result = highest
            engagement_label="search_rank",
            collected_at=now,
        )
        for i, item in enumerate(items)
        if item.get("snippet", {}).get("title") and item.get("id", {}).get("videoId")
    ]
```

### DB Model Change

**File:** `src/infrastructure/db/models.py`

Add one column to `OpportunityModel`:

```python
evidence_json: Mapped[str] = mapped_column(
    Text, nullable=False, default="[]", server_default="[]"
)
```

- `server_default='[]'` ensures existing rows and new rows without evidence serialize to
  an empty JSON array without a backfill migration.
- `nullable=False` with `server_default` is safe for both SQLite and PostgreSQL.

**Alembic migration** (new file under `alembic/versions/`):

```python
def upgrade() -> None:
    op.add_column(
        "opportunities",
        sa.Column("evidence_json", sa.Text(), nullable=False, server_default="[]"),
    )

def downgrade() -> None:
    op.drop_column("opportunities", "evidence_json")
```

No data backfill. Old rows will read `evidence_json='[]'` and deserialize to `[]`.

### Repository Change

**File:** `src/infrastructure/db/repositories.py`

**On save** (`SQLBriefingRepository.save`): serialize `opp.evidence` before writing.

```python
import dataclasses, json

def _serialize_evidence(items: list[EvidenceItem]) -> str:
    return json.dumps([
        {**dataclasses.asdict(e), "collected_at": e.collected_at.isoformat()}
        for e in items
    ])
```

**On load** (`_to_opportunity` mapper): deserialize from JSON.

```python
from domain.value_objects.evidence_item import EvidenceItem
from datetime import datetime

def _deserialize_evidence(raw: str) -> list[EvidenceItem]:
    try:
        items = json.loads(raw or "[]")
        return [
            EvidenceItem(
                **{**item, "collected_at": datetime.fromisoformat(item["collected_at"])}
            )
            for item in items
        ]
    except Exception:
        return []
```

The `except Exception: return []` guard satisfies FR-5: malformed or missing JSON never
raises — it degrades to empty evidence.

---

## Application Layer Changes

### `RunPipelineUseCase`

**File:** `src/application/use_cases/run_pipeline.py`

Two changes:
1. After `asyncio.gather()` on collectors, read `_last_evidence` from adapters that have it.
2. Build a per-topic evidence registry, cap items, and attach to each `Opportunity`.

```python
async def _collect_all(self, keywords: list[str]) -> tuple[list[TrendSignal], list[EvidenceItem]]:
    tasks = [self._safe_collect(collector, keywords) for collector in self._collectors]
    results = await asyncio.gather(*tasks)

    all_signals: list[TrendSignal] = []
    all_evidence: list[EvidenceItem] = []
    for collector, batch in zip(self._collectors, results):
        all_signals.extend(batch)
        if hasattr(collector, "_last_evidence"):
            all_evidence.extend(collector._last_evidence)

    return all_signals, all_evidence


def _build_evidence_for_topic(
    self, topic: str, evidence: list[EvidenceItem]
) -> list[EvidenceItem]:
    topic_evidence = [e for e in evidence if e.topic == topic]
    by_type: dict[str, list[EvidenceItem]] = {}
    for item in topic_evidence:
        by_type.setdefault(item.signal_type, []).append(item)

    result: list[EvidenceItem] = []
    for items in by_type.values():
        top5 = sorted(items, key=lambda e: e.engagement_count, reverse=True)[:5]
        result.extend(top5)

    # global cap: max 15
    return sorted(result, key=lambda e: e.engagement_count, reverse=True)[:15]
```

The `execute()` method unpacks the tuple and attaches evidence after creating opportunities:

```python
signals, evidence = await self._collect_all(niche.keywords)
# ... scoring unchanged ...
opportunities = [
    Opportunity.create(topic=topic, score=score)
    for topic, score in scores.items()
]
for opp in opportunities:
    opp.evidence = self._build_evidence_for_topic(opp.topic, evidence)
```

Note: `Opportunity` is not `frozen=True` — mutating `opp.evidence` after construction
is safe (the entity is a regular `@dataclass`).

---

## API Layer Changes

### New Schema: `EvidenceItemResponse`

**File:** `src/api/schemas/opportunity.py`

```python
class EvidenceItemResponse(BaseModel):
    source: str
    signal_type: str
    topic: str
    title: str
    url: str | None
    engagement_count: int
    engagement_label: str
    collected_at: str          # ISO 8601 string — simpler than datetime for JSON clients
```

### Updated `OpportunityResponse`

```python
class OpportunityResponse(BaseModel):
    id: str
    topic: str
    score: OpportunityScoreResponse
    recommended_action: str
    evidence: list[EvidenceItemResponse] = []   # NEW — always present, defaults to []
```

### Briefing route mapping

**File:** `src/api/routes/briefing.py`

The route that maps `Opportunity → OpportunityResponse` adds:

```python
evidence=[
    EvidenceItemResponse(
        source=e.source,
        signal_type=e.signal_type,
        topic=e.topic,
        title=e.title,
        url=e.url,
        engagement_count=e.engagement_count,
        engagement_label=e.engagement_label,
        collected_at=e.collected_at.isoformat(),
    )
    for e in opp.evidence
]
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| `TrendDataPort` contract | Unchanged | FR-9; avoids breaking all 5 existing adapters and their tests |
| Evidence side-channel | `_last_evidence` instance variable | Minimal non-breaking mechanism; no new port required |
| Capping strategy | Top-5 per signal_type, max 15 per opportunity | Bounds storage; preserves most valuable items per signal dimension |
| Persistence | `evidence_json TEXT` on `OpportunityModel` | Single additive migration; JSON is queryable enough for v1 |
| Serialization format | `dataclasses.asdict` + ISO 8601 datetime | No external dependency; reversible with `fromisoformat` |
| YouTube engagement proxy | Search rank position | `search().list(part="snippet")` has no view count; adding `videos.list` would be a separate HTTP call per video — deferred |
| SERP engagement proxy | Inverted rank position (organic) / ad position | CPC data not available from SerpAPI basic results without additional params — deferred |
| `EvidenceItem.url` nullability | `str | None` | HN Ask posts and some SERP ads may lack a direct URL; must not fail |
| Backfill | None | `server_default='[]'` makes old rows safe; retroactive backfill is out of scope |

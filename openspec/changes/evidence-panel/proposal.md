# Proposal: Evidence Panel

## Context

Every opportunity in the system has a numeric score (e.g. `total: 8.4`) but
no explanation of why that score was reached. The five adapters (Reddit, HackerNews,
SERP, YouTube, Google Trends) fetch rich data — posts with upvotes, videos with view
counts, ads indicating purchase intent — and immediately discard it, reducing everything
to a single float. PropFlow users have no way to validate a score, trust it, or act on it.

The Evidence Panel closes this gap: when a user sees "Score 8.4", they can inspect the
actual posts, threads, and SERP signals that produced it, building trust in the system
and enabling faster editorial decisions.

---

## Option A — Enrich TrendSignal (in-place enrichment)

**How it works:**
Add optional fields directly to `TrendSignal`: `url: str | None`, `title: str | None`,
`engagement_count: int | None`, `evidence_label: str | None`. Each adapter populates these
when it has them. The scoring engine ignores the new fields (it only reads `raw_value`).
After scoring, evidence is extracted from signals and attached to `Opportunity`. A single
JSON column `evidence_json` is added to `OpportunityModel`.

**Advantages:**
- Minimal new types — one dataclass change
- Evidence and signal travel together; no synchronization needed
- Port signature (`collect() -> list[TrendSignal]`) stays the same

**Disadvantages:**
- `TrendSignal` conflates two concerns: a scoring input signal and a human-readable evidence item. These have different lifecycles — signals can be discarded after scoring; evidence must be persisted.
- A frozen dataclass with 9 fields starts to smell. `raw_value=0.73` alongside `url="https://reddit.com/r/..."` is a leaky abstraction.
- Google Trends produces no URL or title by design — its `TrendSignal` would always have `None` evidence fields, making the type semantically inconsistent.
- Downstream consumers (ScoringEngine, any future ML layer) now receive noise fields they must consciously ignore.

**Best when:** The project is a prototype, the team is tiny, and the architecture can
tolerate a little pragmatic coupling to move fast.

---

## Option B — Separate EvidenceItem value object + AdapterResult (recommended)

**How it works:**
Introduce a new `EvidenceItem` value object in `domain/value_objects/evidence_item.py`:

```python
@dataclass(frozen=True)
class EvidenceItem:
    source: str            # "reddit" | "hacker_news" | "serp" | "youtube"
    signal_type: str       # mirrors TrendSignal.signal_type
    topic: str
    url: str
    title: str
    engagement_count: int  # upvotes, points, views, ad count
    engagement_label: str  # "upvotes" | "points" | "views" | "ads"
    collected_at: datetime
```

Adapters that can produce evidence return an `AdapterResult(signals, evidence)` named tuple
from an internal helper — but **the public `TrendDataPort.collect()` contract is unchanged**.
The use case calls a new internal method `collect_with_evidence()` that the adapters
implement optionally via a mixin or a second optional port `EvidencePort`.

`RunPipelineUseCase` collects both lists, runs scoring on signals as today, then attaches
top-N evidence items (by `engagement_count`) to each `Opportunity`:

```python
opportunity.evidence = evidence_registry.top_for_topic(topic, limit=5)
```

`Opportunity` gains `evidence: list[EvidenceItem] = field(default_factory=list)`.

Persistence: a single `Text` column `evidence_json` on `OpportunityModel` stores
JSON-serialized evidence (top 5 per signal type, max 15 total per opportunity).
No new table, no migration complexity, no extra join.

API: `OpportunityResponse` gains `evidence: list[EvidenceItemResponse]` and the briefing
route maps it through.

**Advantages:**
- Clean separation of concerns: `TrendSignal` stays a pure scoring input; `EvidenceItem` is a human-readable trace record.
- `TrendDataPort` contract is never touched — all existing tests pass unchanged.
- `ScoringEngine` receives the same `list[TrendSignal]` as today, zero coupling to evidence.
- Evidence can evolve independently (add CPC, thumbnail, sentiment) without touching signal scoring.
- Adapters opt in progressively: Reddit, HN, SERP, YouTube can all produce evidence; GoogleTrends (no URLs) simply returns an empty list.
- JSON column keeps the migration to a single `ALTER TABLE` with a `server_default='[]'`, making backfill trivial (old rows return empty evidence gracefully).
- Top-N capping (5 per signal type, 15 per opportunity) controls storage growth at the source.

**Disadvantages:**
- More types to introduce upfront: `EvidenceItem`, `EvidenceItemResponse`, `EvidenceRegistry` (thin helper to group and rank items by topic).
- Adapters that produce evidence need a small refactor to return `(signals, evidence)` internally, then expose evidence separately.
- `RunPipelineUseCase` grows slightly in complexity to wire both collections.

**Best when:** The architecture needs to stay clean, the evidence schema will evolve
(adding CPC, sentiment, thumbnails), and the team cares about testability.

---

## Recommended Option

**Option B.**

The architectural cost of Option A is hidden but real: polluting `TrendSignal` with
display-layer fields violates the single-responsibility principle at the domain layer and
couples the scoring pipeline to evidence concerns it has no business knowing about. Option B
costs a bit more upfront but keeps every layer focused, lets the scoring engine evolve
independently of evidence schema changes, and produces clean API output that PropFlow can
depend on. The JSON column approach avoids over-engineering with a separate table while
still being easily migrated later if query patterns demand it.

---

## Scope

**In scope:**
- New `EvidenceItem` value object in domain layer
- `EvidenceItemResponse` Pydantic schema
- Internal evidence collection in Reddit, HackerNews, SERP, and YouTube adapters (top-5 per run)
- `evidence: list[EvidenceItem]` field on `Opportunity` entity (default empty list)
- `evidence_json` Text column on `OpportunityModel` (additive migration, `server_default='[]'`)
- Evidence serialization/deserialization in `SQLBriefingRepository`
- `evidence` field in `OpportunityResponse` and the briefing API route mapping
- Unit tests for evidence collection per adapter
- Integration test verifying evidence appears in `GET /briefing/{niche_id}` response

**Out of scope:**
- Google Trends evidence (the source produces no individual URLs or titles by design)
- A dedicated `evidence_items` relational table (JSON column is sufficient for v1)
- Retroactive backfill of evidence for existing opportunities
- Evidence search / filter endpoints
- CPC or ad price extraction from SERP (can be added in a later task once the EvidenceItem type stabilizes)
- Evidence for `ProductOpportunityModel` / product discovery pipeline
- Sentiment analysis on evidence items

---

## Affected Files (estimated)

**New files:**
- `src/domain/value_objects/evidence_item.py` — `EvidenceItem` dataclass
- `tests/unit/test_evidence_collection.py` — adapter-level evidence unit tests

**Modified files:**
- `src/domain/entities/opportunity.py` — add `evidence: list[EvidenceItem]` field
- `src/infrastructure/adapters/reddit.py` — collect top-5 posts as EvidenceItem
- `src/infrastructure/adapters/hacker_news.py` — collect top-5 hits as EvidenceItem
- `src/infrastructure/adapters/serp.py` — collect top-5 organic + ads as EvidenceItem
- `src/infrastructure/adapters/youtube.py` — collect top-5 video items as EvidenceItem
- `src/application/use_cases/run_pipeline.py` — wire evidence from adapters to opportunities
- `src/infrastructure/db/models.py` — add `evidence_json` column to `OpportunityModel`
- `src/infrastructure/db/repositories.py` — serialize/deserialize evidence in mappers
- `src/api/schemas/opportunity.py` — add `EvidenceItemResponse` + `evidence` on `OpportunityResponse`
- `src/api/routes/briefing.py` — map evidence in response construction
- `alembic/versions/` — new migration adding `evidence_json` column

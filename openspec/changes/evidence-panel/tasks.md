# Tasks: Evidence Panel

## Phase 1 — Domain

- [ ] **1.1** Create `EvidenceItem` frozen dataclass in `src/domain/value_objects/evidence_item.py`
  - Fields: `source`, `signal_type`, `topic`, `title`, `url: str | None`, `engagement_count: int`, `engagement_label`, `collected_at: datetime`
  - Use `from __future__ import annotations` and `@dataclass(frozen=True)`
  - No external dependencies (pure domain type)

- [ ] **1.2** Add `evidence: list[EvidenceItem] = field(default_factory=list)` to `Opportunity` entity in `src/domain/entities/opportunity.py`
  - Import `EvidenceItem` from `domain.value_objects.evidence_item`
  - The `Opportunity.create()` class method requires no change (field has a default)
  - Verify existing unit tests still pass (entity is not frozen — mutation is safe)

---

## Phase 2 — Infrastructure: DB

- [ ] **2.1** Add `evidence_json` column to `OpportunityModel` in `src/infrastructure/db/models.py`
  - `Mapped[str] = mapped_column(Text, nullable=False, default="[]", server_default="[]")`
  - Column goes after `domain_reasoning`, before `created_at`

- [ ] **2.2** Generate Alembic migration for the new column
  - Run: `alembic revision --autogenerate -m "add evidence_json to opportunities"`
  - Review generated migration: must be purely additive (`add_column`)
  - Verify `upgrade()` uses `server_default="[]"` so existing rows get a valid JSON default
  - Verify `downgrade()` calls `op.drop_column("opportunities", "evidence_json")`

- [ ] **2.3** Update `SQLBriefingRepository` in `src/infrastructure/db/repositories.py`
  - Add `_serialize_evidence(items: list[EvidenceItem]) -> str` helper function (module-level)
    - Uses `dataclasses.asdict` + ISO 8601 `collected_at.isoformat()`
  - Add `_deserialize_evidence(raw: str) -> list[EvidenceItem]` helper function (module-level)
    - Parses JSON, reconstructs `EvidenceItem` dataclasses with `datetime.fromisoformat`
    - Catches all exceptions and returns `[]` to satisfy FR-5
  - In `SQLBriefingRepository.save()`: pass `evidence_json=_serialize_evidence(opp.evidence)` when building `OpportunityModel`
  - In `_to_opportunity()` mapper: pass `evidence=_deserialize_evidence(model.evidence_json)` when constructing `Opportunity`

---

## Phase 3 — Infrastructure: Adapters

Each adapter task follows the same pattern:
1. Add `self._last_evidence: list[EvidenceItem] = []` as instance attribute (initialized in `__init__` or at top of `collect()`)
2. Add private `_collect_evidence(keyword, raw_data) -> list[EvidenceItem]` method
3. Call `_collect_evidence()` inside the existing `_fetch()` method, assign result to `self._last_evidence`
4. Wrap evidence collection in try/except — on failure set `self._last_evidence = []` and continue

- [ ] **3.1** `src/infrastructure/adapters/reddit.py` — `_collect_evidence(keyword, posts)`
  - Input: `posts` is the `list[praw.models.Submission]` already fetched in `_fetch()`
  - `EvidenceItem` per post: `source="reddit"`, `signal_type="social_signal"`, `title=post.title`, `url=f"https://reddit.com{post.permalink}"`, `engagement_count=post.score`, `engagement_label="upvotes"`
  - Filter: only posts with `post.score > 0` and non-empty `post.title`
  - Cap: sort by `engagement_count` descending, return top 5

- [ ] **3.2** `src/infrastructure/adapters/hacker_news.py` — `_collect_evidence(keyword, hits)`
  - Input: `hits` is `data.get("hits", [])` already parsed in `_fetch()`
  - `EvidenceItem` per hit: `source="hacker_news"`, `signal_type="social_signal"`, `title=hit.get("title","")`, `url=hit.get("url")` (nullable — Ask HN posts have no external URL), `engagement_count=hit.get("points",0)`, `engagement_label="points"`
  - Filter: only hits with `points > 0` and non-empty title
  - Cap: sort by `engagement_count` descending, return top 5

- [ ] **3.3** `src/infrastructure/adapters/serp.py` — `_collect_evidence(keyword, results_dict)`
  - Input: `results` is the full SerpAPI response dict already fetched in `_fetch()`
  - Two evidence streams from the same response:
    - Organic results → `signal_type="competition_gap"`, `engagement_label="rank"`, `engagement_count = max(10 - i, 1)` (rank-inverted)
    - Ad results → `signal_type="monetization_intent"`, `engagement_label="ad_position"`, `engagement_count = max(5 - i, 1)`
  - Cap: 5 organic items + 5 ad items (each stream capped independently before combining)
  - `url` from `result.get("link")` (nullable)

- [ ] **3.4** `src/infrastructure/adapters/youtube.py` — `_collect_evidence(keyword, items)`
  - Input: `items` is `response.get("items", [])` already fetched in `_fetch()`
  - `EvidenceItem` per item: `source="youtube"`, `signal_type="social_signal"`, `title=item["snippet"]["title"]`, `url=f"https://youtube.com/watch?v={item['id']['videoId']}"`, `engagement_count=max(len(items) - i, 1)`, `engagement_label="search_rank"`
  - Filter: only items with valid `snippet.title` and `id.videoId`
  - No additional sorting needed (already ordered by viewCount from the API query)

---

## Phase 4 — Application

- [ ] **4.1** Update `RunPipelineUseCase` in `src/application/use_cases/run_pipeline.py`
  - Change `_collect_all()` return type to `tuple[list[TrendSignal], list[EvidenceItem]]`
  - After `asyncio.gather()`, iterate `zip(self._collectors, results)` and collect `collector._last_evidence` when `hasattr(collector, "_last_evidence")`
  - Add `_build_evidence_for_topic(topic, evidence) -> list[EvidenceItem]` method:
    - Filter by `e.topic == topic`
    - Group by `signal_type`
    - Per group: sort by `engagement_count` desc, keep top 5
    - Global cap: sort combined result by `engagement_count` desc, keep top 15
  - In `execute()`: unpack `signals, evidence = await self._collect_all(niche.keywords)`
  - After creating `opportunities`, assign: `opp.evidence = self._build_evidence_for_topic(opp.topic, evidence)` for each opportunity
  - Import `EvidenceItem` at the top of the file

---

## Phase 5 — API

- [ ] **5.1** Add `EvidenceItemResponse` Pydantic model to `src/api/schemas/opportunity.py`
  - Fields: `source: str`, `signal_type: str`, `topic: str`, `title: str`, `url: str | None`, `engagement_count: int`, `engagement_label: str`, `collected_at: str` (ISO 8601 string)
  - Use `from __future__ import annotations` and inherit from `BaseModel`

- [ ] **5.2** Update `OpportunityResponse` in `src/api/schemas/opportunity.py`
  - Add `evidence: list[EvidenceItemResponse] = []`
  - Field is always present (not optional) — empty list is the zero value

- [ ] **5.3** Update briefing route in `src/api/routes/briefing.py`
  - In the `Opportunity → OpportunityResponse` mapping, add `evidence` list comprehension
  - Each `EvidenceItem` maps to `EvidenceItemResponse` with `collected_at=e.collected_at.isoformat()`
  - Import `EvidenceItemResponse` from `api.schemas.opportunity`

---

## Phase 6 — Tests

- [ ] **6.1** Unit tests for `EvidenceItem` value object — `tests/unit/test_evidence_item.py`
  - Test: `EvidenceItem` is immutable (frozen dataclass — any mutation raises `FrozenInstanceError`)
  - Test: all required fields must be provided (no hidden defaults)
  - Test: `url=None` is valid (nullable field)

- [ ] **6.2** Unit tests for adapter evidence collection — `tests/unit/test_evidence_collection.py`
  - One `describe` block per adapter with mocked raw responses
  - `test_reddit_collect_evidence_returns_top5_by_score`: mock 8 posts with varying scores, assert only top 5 returned, assert `engagement_label="upvotes"`
  - `test_reddit_collect_evidence_empty_when_no_posts`: mock empty list, assert `[]`
  - `test_hacker_news_collect_evidence_url_nullable_for_ask_posts`: mock hit with `url=None`, assert item is still created
  - `test_serp_collect_evidence_produces_two_signal_types`: mock organic + ads, assert both `competition_gap` and `monetization_intent` items present
  - `test_youtube_collect_evidence_builds_url_from_video_id`: assert `url == "https://youtube.com/watch?v=abc123"`
  - `test_adapter_evidence_empty_on_exception`: mock `_collect_evidence` to raise, assert `_last_evidence == []` and signal still returned

- [ ] **6.3** Unit tests for `RunPipelineUseCase` evidence wiring — `tests/unit/test_run_pipeline.py`
  - `test_execute_attaches_evidence_to_opportunities`: fake adapter with `_last_evidence` populated, assert `opportunity.evidence` is non-empty after `execute()`
  - `test_execute_caps_evidence_at_15_per_opportunity`: fake adapter returns 20 evidence items for one topic, assert max 15 attached
  - `test_execute_caps_evidence_at_5_per_signal_type`: fake adapter returns 8 items of same signal_type, assert max 5 kept
  - `test_execute_works_when_adapter_has_no_last_evidence`: adapter without `_last_evidence` attribute, assert pipeline completes and evidence is `[]`

- [ ] **6.4** Repository serialization unit tests — `tests/unit/test_repositories.py` (or new file)
  - `test_serialize_evidence_roundtrip`: serialize then deserialize `list[EvidenceItem]`, assert equal
  - `test_deserialize_evidence_returns_empty_on_invalid_json`: pass `"not json"`, assert `[]`
  - `test_deserialize_evidence_returns_empty_on_empty_string`: pass `""`, assert `[]`

- [ ] **6.5** Integration test — `tests/integration/test_evidence_pipeline.py`
  - `test_pipeline_run_produces_opportunities_with_evidence`: full pipeline run with mocked HTTP adapters returning rich data, assert `GET /briefing/{niche_id}` response includes `evidence` array with expected fields
  - `test_old_opportunity_row_returns_empty_evidence`: seed DB with legacy `OpportunityModel` row (no `evidence_json` column value or `evidence_json='[]'`), assert API returns `evidence: []` without error

---

## Implementation Order

```
Phase 1 (Domain) → Phase 2 (DB) → Phase 3 (Adapters) → Phase 4 (Application) → Phase 5 (API) → Phase 6 (Tests)
```

Phases 3 and 5.1 can be parallelized once Phase 1 is complete.
Phase 6.1–6.4 (unit tests) can be written alongside their respective phase.
Phase 6.5 (integration test) requires all phases to be complete.

## Estimated Complexity

| Phase | Complexity | Notes |
|---|---|---|
| 1 — Domain | XS | New file + one-line field addition |
| 2.1–2.2 — DB model + migration | XS | Additive column, autogenerated migration |
| 2.3 — Repository serialization | S | Two helper functions + mapper update |
| 3.1–3.4 — Adapters (×4) | S each | Same pattern per adapter; Reddit slightly more complex (praw objects) |
| 4.1 — Use case wiring | S | Tuple return + evidence grouping logic |
| 5.1–5.3 — API schemas + route | XS | New schema + field addition + mapping |
| 6.1–6.4 — Unit tests | S | Straightforward mocking of internal methods |
| 6.5 — Integration test | M | Requires DB + mocked HTTP adapters |

# Spec: Evidence Panel

## Goal

Expose the raw signals that justify each opportunity score by capturing top evidence items
from each adapter and surfacing them in the briefing API response.

---

## Requirements

### Functional

- **FR-1:** Each opportunity in a briefing includes up to 15 evidence items total (max 5 per signal type).
- **FR-2:** Each `EvidenceItem` carries: `source`, `url` (nullable), `title`, `engagement_count` (int), `engagement_label` (human-readable unit), `signal_type`, `topic`, and `collected_at`.
- **FR-3:** The four opted-in adapters collect evidence internally:
  - **Reddit** — top posts by score: `title` from `post.title`, `url` from `post.url`, `engagement_count` from `post.score`, `engagement_label="upvotes"`, `signal_type="social_signal"`.
  - **HackerNews** — top hits by points: `title` from `hit.title`, `url` from `hit.url`, `engagement_count` from `hit.points`, `engagement_label="points"`, `signal_type="social_signal"`.
  - **SERP** — organic results as `competition_gap` evidence: `title` from result title, `url` from result link, `engagement_count` from result position rank (inverted: `10 - position`), `engagement_label="rank"`, `signal_type="competition_gap"`. Ad results as `monetization_intent` evidence: `title` from ad title, `url` from ad link, `engagement_count` from ad position (5 - position), `engagement_label="ad_position"`, `signal_type="monetization_intent"`.
  - **YouTube** — top videos by result order: `title` from `item.snippet.title`, `url` constructed as `https://youtube.com/watch?v={item.id.videoId}`, `engagement_count` from result index position (10 - index), `engagement_label="search_rank"`, `signal_type="social_signal"`.
- **FR-4:** Google Trends and Product Hunt adapters emit no evidence (they produce no individual URLs or titles by design). This is correct and expected, not a gap.
- **FR-5:** Old opportunity rows with no `evidence_json` column value (pre-migration) or with `evidence_json='[]'` return an empty evidence array — never an error.
- **FR-6:** Evidence items are ranked by `engagement_count` descending before capping. When more than 5 items are collected for a signal type, only the top 5 by `engagement_count` are kept.
- **FR-7:** The `evidence` field appears in `GET /briefing/{niche_id}` response on every `OpportunityResponse` object. It is always present (empty list when no evidence was collected).
- **FR-8:** Evidence collection within an adapter is a best-effort operation: if it fails, an empty list is returned and the pipeline continues normally — the signal is still scored.
- **FR-9:** The `TrendDataPort.collect()` contract is not changed. No existing adapter tests are invalidated.

### Non-Functional

- **NFR-1:** Pipeline wall-clock time increases by less than 10%. Evidence extraction is a pure CPU transformation of data already fetched during signal collection — no additional HTTP calls are made.
- **NFR-2:** `evidence_json` TEXT column. Expected max payload per opportunity: 15 items × ~300 bytes each ≈ 4.5 KB. SQLite/PostgreSQL TEXT columns handle this without issue. If total payload ever exceeds 50 KB per opportunity, the capping logic should be revisited.
- **NFR-3:** Evidence is serialized as a JSON array using `dataclasses.asdict` + `json.dumps`. `collected_at` is stored as ISO 8601 string and parsed back with `datetime.fromisoformat`.
- **NFR-4:** The `evidence` field in `OpportunityResponse` is typed as `list[EvidenceItemResponse]` and always present (not optional) to simplify client contracts.

---

## Scenarios (Given / When / Then)

### Scenario 1 — Reddit adapter with matching posts

**Given** a pipeline run for niche "departamentos zona norte" with keyword "departamentos alquiler"
**When** Reddit returns 8 posts with scores [800, 650, 400, 320, 200, 150, 80, 30]
**Then** `_collect_evidence()` produces 8 `EvidenceItem` objects
**And** after capping, only the top 5 are kept: scores [800, 650, 400, 320, 200]
**And** each item has `source="reddit"`, `signal_type="social_signal"`, `engagement_label="upvotes"`, a non-null `url`, and a non-null `title`

### Scenario 2 — Opportunity with no evidence (Trends-only signal)

**Given** the only adapters that returned signals for topic "X" are GoogleTrends
**When** the use case assembles evidence for topic "X"
**Then** `opportunity.evidence` is an empty list `[]`
**And** the API returns `"evidence": []` — no error, no null

### Scenario 3 — Old opportunity row (pre-migration)

**Given** an `OpportunityModel` row with `evidence_json = '[]'` (server_default applied)
**When** `_to_opportunity()` deserializes the row
**Then** `opportunity.evidence` is `[]`
**And** no exception is raised

### Scenario 4 — More than 5 items from one signal type

**Given** SERP returns 10 organic results for a keyword (competition_gap evidence)
**When** `_collect_evidence()` processes the results
**Then** all 10 are collected internally as candidates
**And** after sorting by `engagement_count` descending, only the top 5 are attached to the opportunity

### Scenario 5 — Mixed adapters, total cap at 15

**Given** Reddit produces 5 social_signal items, HN produces 5 social_signal items, SERP produces 5 competition_gap items + 5 monetization_intent items
**When** `RunPipelineUseCase` aggregates evidence for a topic
**Then** total evidence is capped: 5 social_signal + 5 competition_gap + 5 monetization_intent = 15 items
**And** when two adapters produce the same signal type (Reddit + HN → social_signal), the top 5 across both combined are kept

### Scenario 6 — Adapter evidence collection fails

**Given** the HackerNews adapter raises an exception during `_collect_evidence()`
**When** the pipeline runs
**Then** the signal is still scored normally
**And** evidence for that adapter is an empty list
**And** no exception propagates to the use case

### Scenario 7 — YouTube evidence construction

**Given** YouTube search returns 3 video items with videoIds ["abc", "def", "ghi"]
**When** `_collect_evidence()` processes the response
**Then** each item's `url` is `"https://youtube.com/watch?v={videoId}"`
**And** `engagement_count` is derived from search rank position (index 0 → count 10, index 1 → count 9, index 2 → count 8)

---

## Out of Scope

- Full-text storage of HTML content or raw API responses
- Evidence for GoogleTrends adapter (no individual URLs by design — this is expected, not a gap)
- Evidence for ProductHunt adapter (not yet in active use)
- Evidence for `ProductOpportunityModel` / product discovery pipeline (separate concern)
- A dedicated relational `evidence_items` table (JSON column is the chosen approach for v1)
- Retroactive backfill of evidence for existing opportunity rows
- Evidence search, filter, or aggregation endpoints
- CPC or ad spend extraction from SERP (schema extension for a future iteration)
- Sentiment analysis on evidence item titles
- Evidence deduplication across adapters

# Explore: Evidence Panel

## Current State

### What TrendSignal carries today

`TrendSignal` is a minimal frozen dataclass with five fields:
`source`, `topic`, `raw_value` (0.0–1.0), `signal_type`, and `collected_at`.

There is **no evidence metadata whatsoever** — no URLs, no post titles, no upvote counts,
no view counts, no ad prices, no organic result snippets. The adapter computes a single
float from whatever the external source returns and throws everything else away.

Concrete examples of what gets discarded right now:

| Adapter | Raw data fetched | What survives in TrendSignal |
|---|---|---|
| Reddit | 25 posts (title, URL, score, subreddit) | avg_score → raw_value (0–1) |
| HackerNews | N hits (title, URL, points, author) | avg_points → raw_value (0–1) |
| SERP | organic_results list + ads list | len(organic) and len(ads) → 2 raw_values |
| YouTube | 10 video items (title, videoId, snippet) | len(items) / 10 → raw_value |
| Google Trends | interest_over_time DataFrame | last row value / 100 → raw_value |

### What gets stored in the DB

`OpportunityModel` stores only the five scored dimensions (`trend_velocity`,
`competition_gap`, `social_signal`, `monetization_intent`, `frustration_level`),
`total`, `confidence`, `recommended_action`, `domain_applicability`, and
`domain_reasoning`. No signal-level data is persisted at all.

The pipeline flow is:
```
adapters.collect() → list[TrendSignal]    # raw_value only, no evidence
  → ScoringEngine.score()                 # aggregates raw_values by topic+type
    → dict[topic, OpportunityScore]       # only numeric dimensions
      → Opportunity.create()              # domain entity, score only
        → Briefing → BriefingRepository.save()  # persists opportunity scores
```

Evidence is permanently lost after `collect()` returns.

### Current API response

`GET /briefing/{niche_id}` returns a `BriefingResponse` with a list of
`OpportunityResponse` objects. Each contains: `id`, `topic`, `recommended_action`,
and a `score` object with the five numeric dimensions plus `confidence`. No evidence,
no explanation of why those numbers are what they are.

## Key Questions

1. **Where does evidence live architecturally?**
   Should `EvidenceItem` be a new value object in the domain, or is it purely an
   infrastructure/persistence concern? The domain currently has no notion of raw source data.

2. **TrendSignal enrichment vs separate type?**
   Should `TrendSignal` gain optional evidence fields (`url`, `title`,
   `engagement_count`, `evidence_metadata`), or should a new `EvidenceItem` type exist
   alongside TrendSignal (one signal can produce N evidence items)?

3. **Storage granularity?**
   Storing every piece of evidence for every signal every run could be 25+ rows per
   keyword per adapter per run. What is the right cap? Top-3? Top-5? Only the items
   that most justify the score?

4. **New table vs JSON column?**
   A separate `evidence_items` table gives queryability and clean foreign keys.
   A `evidence_json` column on `OpportunityModel` is simpler and avoids a migration
   that adds a many-to-many join. Which fits the current scale?

5. **Port contract impact?**
   `TrendDataPort.collect()` currently returns `list[TrendSignal]`. Changing it to
   return `list[TrendSignal | EvidenceBundle]` or a richer type breaks all five adapters
   and any future adapter. A non-breaking approach is needed.

6. **Scoring engine coupling?**
   The engine receives `list[TrendSignal]` and operates on `raw_value` only. Evidence
   items must pass through the engine untouched or bypass it entirely, since the engine
   has no business logic for them.

7. **Backfill?**
   Existing opportunities in the DB have no evidence. The feature must degrade gracefully
   (empty evidence list) for historical data.

## Technical Findings

- **The evidence destruction is total and early.** Adapters call `.search()` / `.search().list()` / client HTTP calls and receive rich objects, but immediately reduce them to one float. Capturing evidence requires touching only the adapter layer — the scoring engine and domain entity do not need to change their core logic.

- **`ScoringEngine` uses only `signal.raw_value`** inside `_score_topic`. It groups by `signal.signal_type` and averages `raw_value`. Evidence items can ride alongside signals as a parallel list without touching the engine at all.

- **`OpportunityModel` is a flat table** with no JSON columns today. Adding a `Text` column for JSON-encoded evidence would be a single additive migration. Adding a child table `evidence_items` would require a second migration and a `selectinload` in `SQLBriefingRepository.get_latest`.

- **`Opportunity` domain entity is a plain dataclass** with fields for score and LLM-generated reasoning. Adding an `evidence: list[EvidenceItem]` field is non-breaking if it defaults to an empty list.

- **The briefing route (`GET /briefing/{niche_id}`) maps `Opportunity` → `OpportunityResponse` manually.** This is the exact injection point for evidence in the API response.

- **`RunPipelineUseCase._collect_all()`** gathers all signals from all adapters. This is where parallel evidence collection can be gathered alongside signals without changing the port signature.

- **`frustration_level` is already scaffolded** in the scoring engine and DB but no adapter produces it yet — evidence items for that signal type are also zero today, which means the evidence feature can be added incrementally.

## Hypothesis

The cleanest approach is to introduce a new `EvidenceItem` value object in the domain layer
(with `source`, `url`, `title`, `engagement_count`, `signal_type`, and `collected_at`),
keep `TrendSignal` unchanged, and have adapters return an `AdapterResult` named tuple
containing `(signals: list[TrendSignal], evidence: list[EvidenceItem])`. The use case
collects both without touching the port contract — the port still returns `list[TrendSignal]`,
but adapters that opt in can also populate a parallel evidence registry. Evidence is then
attached to `Opportunity` as `evidence: list[EvidenceItem] = field(default_factory=list)`,
persisted as a JSON column on `OpportunityModel` (top-5 items per signal type, capped at
15 total per opportunity), and exposed via a new `evidence` field in `OpportunityResponse`.
This approach requires zero changes to `TrendDataPort`, `ScoringEngine`, or any existing tests.

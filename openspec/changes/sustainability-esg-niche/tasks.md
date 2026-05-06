# Tasks: ESG & Sustainability LATAM Niche

## Phase 1: Scoring Engine
- [x] 1.1 Implement `ESGScoringEngine` in `src/application/services/scoring_engine.py` with weights: social 0.10, trend 0.15, competition 0.30, monetization 0.20, frustration 0.25.
- [x] 1.2 Update `ScoringFactory` to support `esg_intelligence`.

## Phase 2: Infrastructure & Templates
- [x] 2.1 Add "ESG LATAM" template to `src/infrastructure/niche_templates.py`.
- [x] 2.2 Update `src/config.py` with `ESG_KEYWORDS_LATAM`.

## Phase 3: Application & Adapters
- [x] 3.1 Update Claude adapter prompt logic for ESG implications (`feature`, `contenido`, `posicionamiento`, `irrelevante`).

## Phase 4: Dashboard
- [x] 4.1 Update results table to show "Implicación" for ESG mode.

## Phase 5: Tests
- [x] 5.1 Unit tests for `ESGScoringEngine`.
- [x] 5.2 Integration test for ESG pipeline.

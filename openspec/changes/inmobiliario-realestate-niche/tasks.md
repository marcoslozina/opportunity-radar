# Tasks: PropFlow (Real Estate) Niche

## Phase 1: Domain Refactor
- [x] 1.1 Update `Opportunity` entity in `src/domain/entities/opportunity.py` to add `domain_applicability` and `domain_reasoning`.
- [x] 1.2 Update SQLAlchemy model in `src/infrastructure/db/models.py` to include the new columns.
- [x] 1.3 Create and run Alembic migration for the new columns.

## Phase 2: Scoring Engine Generalization
- [x] 2.1 Refactor `ScoringEngine` in `src/application/services/scoring_engine.py` to accept weights in constructor.
- [x] 2.2 Implement `RealEstateScoringEngine` with weights: social 0.15, trend 0.15, competition 0.20, monetization 0.30, frustration 0.20.
- [x] 2.3 Implement `ScoringFactory` to return correct engine based on `discovery_mode`.

## Phase 3: Infrastructure & Templates
- [x] 3.1 Create `src/infrastructure/niche_templates.py` with `NicheTemplate` dataclass and "PropFlow" template.
- [x] 3.2 Update `src/config.py` with `PROPFLOW_KEYWORDS_AR`.

## Phase 4: Application & Adapters
- [x] 4.1 Update `RunPipelineUseCase` to use `ScoringFactory`.
- [x] 4.2 Update Claude adapter prompt logic to populate `domain_applicability` and `domain_reasoning` for PropFlow mode.

## Phase 5: Dashboard & UI
- [x] 5.1 Update `dashboard.py` to include template selector in "Crear Nicho".
- [x] 5.2 Update results table to show "Aplicabilidad" column for PropFlow.

## Phase 6: Tests
- [x] 6.1 Unit tests for `RealEstateScoringEngine`.
- [x] 6.2 Integration test for full real_estate pipeline.

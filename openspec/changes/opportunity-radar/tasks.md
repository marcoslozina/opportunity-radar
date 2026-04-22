# Tasks: Opportunity Radar

## Phase 1: Project Setup

- [x] 1.1 Inicializar proyecto con `uv init opportunity-radar` dentro de `/home/marcos/Desktop/opportunity-radar`
- [x] 1.2 Crear `pyproject.toml` con deps: `fastapi`, `uvicorn`, `sqlalchemy[asyncio]`, `alembic`, `apscheduler`, `anthropic`, `pytrends`, `praw`, `httpx`, `cachetools`, `google-api-python-client`, `serpapi`, `pydantic-settings`
- [x] 1.3 Agregar deps de dev: `pytest`, `pytest-asyncio`, `respx`, `ruff`, `mypy`
- [x] 1.4 Crear estructura de carpetas vacía: `src/domain/`, `src/application/`, `src/infrastructure/`, `src/api/`, `tests/unit/`, `tests/integration/`
- [x] 1.5 Crear `src/config.py` con `pydantic-settings`: `DATABASE_URL`, `ANTHROPIC_API_KEY`, `PIPELINE_SCHEDULE`, claves de APIs externas

## Phase 2: Domain Layer

- [x] 2.1 Crear `src/domain/entities/niche.py` — dataclass `Niche` con `id: NicheId`, `name: str`, `keywords: list[str]`; método `create()`
- [x] 2.2 Crear `src/domain/value_objects/trend_signal.py` — dataclass frozen `TrendSignal` con `source`, `topic`, `raw_value: float`, `signal_type`, `collected_at`
- [x] 2.3 Crear `src/domain/value_objects/opportunity_score.py` — dataclass frozen `OpportunityScore` con 4 dimensiones (0–10) + `total: float` (0–100) + `confidence: str`; método `from_dimensions()`
- [x] 2.4 Crear `src/domain/entities/opportunity.py` — dataclass `Opportunity` con `topic`, `score: OpportunityScore`, `recommended_action: str`
- [x] 2.5 Crear `src/domain/entities/briefing.py` — dataclass `Briefing` con `niche_id`, `opportunities: list[Opportunity]`, `generated_at`; propiedad `top_10`
- [x] 2.6 Crear `src/domain/ports/trend_data_port.py` — ABC `TrendDataPort` con `collect(keywords: list[str]) -> list[TrendSignal]`
- [x] 2.7 Crear `src/domain/ports/insight_port.py` — ABC `InsightPort` con `synthesize(opportunities: list[Opportunity]) -> list[str]`
- [x] 2.8 Crear `src/domain/ports/repository_ports.py` — ABCs: `NicheRepository`, `OpportunityRepository`, `BriefingRepository`

## Phase 3: Application Layer

- [x] 3.1 Crear `src/application/services/scoring_engine.py` — `ScoringEngine.score(signals: list[TrendSignal]) -> list[OpportunityScore]`; normalización min-max por fuente + weighted avg; marca `confidence: "low"` si < 2 fuentes
- [x] 3.2 Crear `src/application/use_cases/create_niche.py` — valida keywords no vacías (raise `KeywordsRequiredError`), persiste vía `NicheRepository`
- [x] 3.3 Crear `src/application/use_cases/run_pipeline.py` — orquesta: `asyncio.gather()` sobre adapters → `ScoringEngine.score()` → `InsightPort.synthesize()` → `BriefingRepository.save()`; captura errores por adapter sin fallar el pipeline
- [x] 3.4 Crear `src/application/use_cases/get_briefing.py` — retorna `BriefingRepository.get_latest(niche_id)`; retorna lista vacía si no existe (no error)

## Phase 4: Infrastructure — DB

- [x] 4.1 Crear `src/infrastructure/db/models.py` — SQLAlchemy ORM models: `NicheModel`, `OpportunityModel`, `BriefingModel` con UUIDs, timestamps
- [x] 4.2 Crear `src/infrastructure/db/session.py` — async engine factory, `get_session()` dependency
- [x] 4.3 Crear `src/infrastructure/db/repositories.py` — implementaciones concretas de los 3 repos con SQLAlchemy async
- [x] 4.4 Inicializar Alembic (`alembic init alembic/`) y crear migración inicial con los 3 modelos

## Phase 5: Infrastructure — Adapters

- [x] 5.1 Crear `src/infrastructure/adapters/hacker_news.py` — httpx → `https://hn.algolia.com/api/v1/search`; retorna señales `social_signal`
- [x] 5.2 Crear `src/infrastructure/adapters/reddit.py` — praw; busca posts por keyword, retorna señales `social_signal`
- [x] 5.3 Crear `src/infrastructure/adapters/google_trends.py` — pytrends; retorna señal `trend_velocity`; TTLCache de 1h
- [x] 5.4 Crear `src/infrastructure/adapters/youtube.py` — google-api-python-client; busca videos por keyword, retorna señal `social_signal`
- [x] 5.5 Crear `src/infrastructure/adapters/product_hunt.py` — httpx GraphQL; retorna señales `monetization_intent`
- [x] 5.6 Crear `src/infrastructure/adapters/serp.py` — serpapi; retorna `competition_gap` (dificultad keyword) + `monetization_intent` (CPC)
- [x] 5.7 Crear `src/infrastructure/adapters/claude_insight.py` — anthropic SDK, `claude-sonnet-4-6`, prompt caching; genera `recommended_action` por oportunidad

## Phase 6: Infrastructure — Scheduler

- [x] 6.1 Crear `src/infrastructure/scheduler/pipeline_scheduler.py` — APScheduler `AsyncIOScheduler`; job semanal por nicho activo; `coalesce=True`, `max_instances=1`; loggea `PIPELINE_ALREADY_RUNNING` si hay conflicto

## Phase 7: API Layer

- [x] 7.1 Crear `src/api/routes/health.py` — `GET /health` retorna `{"status": "ok", "scheduler": "running"|"stopped"}`
- [x] 7.2 Crear `src/api/routes/niches.py` — `POST /niches` (201), `GET /niches` (200), `DELETE /niches/{id}` (204); schemas Pydantic separados de entidades
- [x] 7.3 Crear `src/api/routes/opportunities.py` — `GET /opportunities?niche_id=` con paginación cursor
- [x] 7.4 Crear `src/api/routes/briefing.py` — `GET /briefing/{niche_id}` retorna último briefing o 404
- [x] 7.5 Crear `src/api/middleware/logging.py` — middleware que loggea `request_id`, `method`, `path`, `status`, `duration_ms`
- [x] 7.6 Crear `src/main.py` — FastAPI app factory, lifespan con APScheduler, incluir routers, DI wiring manual

## Phase 8: Tests

- [x] 8.1 Tests unitarios `tests/unit/test_scoring_engine.py` — score con ≥ 3 fuentes, confidence "low" con 1 fuente, weighted avg correcto
- [x] 8.2 Tests unitarios `tests/unit/test_briefing.py` — top_10 ordering, retorna disponibles si < 10
- [x] 8.3 Tests de use cases `tests/unit/test_create_niche.py` — happy path, `KEYWORDS_REQUIRED` error
- [x] 8.4 Tests de use cases `tests/unit/test_run_pipeline.py` — fallo de 1 adapter no rompe pipeline, señales integradas correctamente
- [x] 8.5 Tests de integración `tests/integration/test_hacker_news_adapter.py` — respx fixtures
- [x] 8.6 Tests de API `tests/integration/test_api_niches.py` — TestClient: POST 201, POST 422 keywords vacías, DELETE 204
- [x] 8.7 Tests de API `tests/integration/test_api_briefing.py` — GET briefing 200 con datos, GET 404 sin datos

## Phase 9: ADRs + Docs

- [x] 9.1 Crear `docs/adr/ADR-001-clean-architecture.md` — documenta decisión de Clean Architecture + Ports & Adapters
- [x] 9.2 Crear `docs/adr/ADR-002-apscheduler-embedded.md` — documenta elección de APScheduler vs Celery
- [x] 9.3 Actualizar `README.md` con setup local, variables de entorno requeridas y cómo correr el pipeline manualmente

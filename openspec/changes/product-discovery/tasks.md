# Tasks: Product Discovery

## Phase 1: Domain — Value Objects & Enums

- [x] 1.1 Crear `src/domain/value_objects/product_type.py` — Enum `ProductType(str, Enum)`: EBOOK, MICRO_SAAS, SERVICE, DIGITAL_PRODUCT
- [x] 1.2 Crear `src/domain/value_objects/profitability_score.py` — `@dataclass(frozen=True) ProfitabilityScore` con dims (0–10): frustration_level, market_size, competition_gap, willingness_to_pay + total (0–100) + confidence; método `from_dimensions()`
- [x] 1.3 Modificar `src/domain/entities/niche.py` — agregar `discovery_mode: str = "content"` al dataclass `Niche`

## Phase 2: Domain — Entities & Ports

- [x] 2.1 Crear `src/domain/entities/product_opportunity.py` — `@dataclass ProductOpportunity`: id, niche_id, topic, score (ProfitabilityScore), product_type (ProductType | None), product_reasoning (str), recommended_price_range (str), created_at
- [x] 2.2 Crear `src/domain/entities/product_briefing.py` — `@dataclass ProductBriefing`: id, niche_id, opportunities (list[ProductOpportunity]), generated_at; propiedad `top_5` ordenada por score.total desc
- [x] 2.3 Crear `src/domain/ports/product_discovery_port.py` — ABC `ProductDiscoveryPort.classify(opportunities: list[ProductOpportunity]) -> list[ProductClassification]`; `@dataclass(frozen=True) ProductClassification`: product_type, reasoning, recommended_price_range
- [x] 2.4 Crear `src/domain/ports/product_repository_ports.py` — ABCs `ProductOpportunityRepository` (save, get_by_niche) y `ProductBriefingRepository` (save, get_latest)

## Phase 3: Application Layer

- [x] 3.1 Crear `src/application/services/profitability_scoring_engine.py` — `ProfitabilityScoringEngine.score(signals: list[TrendSignal]) -> list[tuple[str, ProfitabilityScore]]`; normaliza 4 dims por topic; confidence "low" < 2 fuentes
- [x] 3.2 Crear `src/application/use_cases/run_product_discovery.py` — orquesta: asyncio.gather(FrustrationSignalAdapter×2, SerpProductAdapter, SerpAdapter) → ProfitabilityScoringEngine → ProductDiscoveryPort.classify → ProductBriefingRepository.save; captura errores por adapter
- [x] 3.3 Crear `src/application/use_cases/get_product_briefing.py` — retorna `ProductBriefingRepository.get_latest(niche_id)`; lanza `ProductBriefingNotFoundError` si no existe

## Phase 4: Infrastructure — Adapters

- [x] 4.1 Crear `src/infrastructure/adapters/frustration_signal.py` — `FrustrationSignalAdapter(TrendDataPort)` para Reddit y HN; query patterns: "is there a tool", "why is there no", "I do this manually"; retorna signals con signal_type="frustration_level"
- [x] 4.2 Crear `src/infrastructure/adapters/serp_product.py` — `SerpProductAdapter(TrendDataPort)` usando serpapi; queries "X software", "X tool", "alternatives to X"; retorna signal_type="competition_gap"
- [x] 4.3 Crear `src/infrastructure/adapters/claude_product_discovery.py` — `ClaudeProductDiscoveryAdapter(ProductDiscoveryPort)` con anthropic SDK; prompt con topic + score dims + señales → ProductType + reasoning + price_range; fallback "digital-product" si baja confianza

## Phase 5: Infrastructure — DB & Scheduler

- [x] 5.1 Modificar `src/infrastructure/db/models.py` — agregar `ProductOpportunityModel`, `ProductBriefingModel` (tablas product_opportunities, product_briefings); agregar columna `discovery_mode VARCHAR(10) DEFAULT 'content'` en `NicheModel`
- [x] 5.2 Crear `src/infrastructure/db/product_repositories.py` — SQLAlchemy async impls de `ProductOpportunityRepository` y `ProductBriefingRepository`
- [x] 5.3 Modificar `src/infrastructure/scheduler/pipeline_scheduler.py` — `add_product_discovery_job(niche)` si `discovery_mode in ("product", "both")`; prefijo `product_pipeline_` en job IDs
- [x] 5.4 Crear migración Alembic — tablas `product_briefings`, `product_opportunities`; columna `discovery_mode` en niches; aditiva, sin tocar tablas existentes

## Phase 6: API Layer

- [x] 6.1 Crear `src/api/schemas/product_opportunity.py` — Pydantic v2 schemas: `ProfitabilityScoreResponse`, `ProductOpportunityResponse`, `ProductBriefingResponse`
- [x] 6.2 Crear `src/api/routes/product_briefing.py` — `GET /product-briefing/{niche_id}` → `GetProductBriefingUseCase` → `ProductBriefingResponse`; 404 si no existe
- [x] 6.3 Modificar `src/main.py` — incluir router de product_briefing; DI wiring para `ClaudeProductDiscoveryAdapter` y product repos
- [x] 6.4 Modificar `src/api/routes/niches.py` y schemas — aceptar y retornar `discovery_mode`; validar valores válidos ("content", "product", "both"); 422 si inválido

## Phase 7: Tests

- [x] 7.1 `tests/unit/test_profitability_score.py` — from_dimensions(), confidence "low" con 1 fuente, total 0–100
- [x] 7.2 `tests/unit/test_product_briefing.py` — top_5 ordering, retorna disponibles si < 5
- [x] 7.3 `tests/unit/test_run_product_discovery.py` — fallo de 1 adapter no rompe pipeline; clasificación OK con fake adapters
- [x] 7.4 `tests/integration/test_frustration_signal_adapter.py` — respx mock HN + Reddit; señales correctas
- [x] 7.5 `tests/integration/test_api_product_briefing.py` — GET 200 top 5, GET 404 sin briefing
- [x] 7.6 `tests/integration/test_api_niches.py` (extend) — POST con discovery_mode "product" → 201; POST con "unknown" → 422

## Phase 8: ADR

- [x] 8.1 Crear `docs/adr/ADR-003-product-discovery-domain.md` — documenta separación del dominio product-discovery vs content; descarta nullable columns en Opportunity; justifica FrustrationSignalAdapter implementando TrendDataPort existente

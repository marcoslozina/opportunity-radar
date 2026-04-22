# Proposal: Product Discovery

## Intent

Creators e indie makers no solo necesitan saber sobre qué crear contenido — necesitan saber qué **producto construir o vender**. El Opportunity Radar hoy responde "¿sobre qué escribir?". Esta feature responde "¿qué me conviene construir y cuánto puedo cobrar?". Son preguntas distintas que requieren señales distintas: frustración, tamaño de mercado, competencia de productos y disposición a pagar.

## Scope

### In Scope
- Nuevas entidades de dominio: `ProductOpportunity`, `ProductBriefing`, `ProfitabilityScore` (VO), `ProductType` (enum)
- Port nuevo: `ProductDiscoveryPort` (separado de `InsightPort`)
- Adapter nuevo: `FrustrationSignalAdapter` (Reddit + HN con query patterns de pain points)
- `SerpAdapter` extendido con query de competencia de productos
- Use case nuevo: `RunProductDiscoveryUseCase`
- `Niche` gana campo `discovery_mode: "content" | "product" | "both"`
- DB: tablas nuevas `product_briefings` + `product_opportunities` (sin tocar tablas existentes)
- API: `GET /product-briefing/{niche_id}`
- Scheduler: corre product discovery cuando `discovery_mode` incluye "product"

### Out of Scope
- UI/frontend
- Price validation contra marketplaces reales (Gumroad, AppSumo)
- Competitor deep-dive (análisis detallado de productos existentes)
- MVP scoring (¿cuánto cuesta construirlo?)

## Approach

Dominio completamente separado del flujo de content opportunities. `ProductOpportunity` tiene su propio `ProfitabilityScore` con 4 dimensiones propias: `frustration_level`, `market_size`, `competition_gap`, `willingness_to_pay`. Claude (`ProductDiscoveryPort`) recibe topic + scores + señales → devuelve `ProductType` + `product_reasoning` + `recommended_price_range`. Misma arquitectura Ports & Adapters, sin tocar entidades existentes.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/domain/entities/` | New | `ProductOpportunity`, `ProductBriefing` |
| `src/domain/value_objects/` | New | `ProfitabilityScore`, `ProductType` |
| `src/domain/ports/` | New | `ProductDiscoveryPort`, `ProductOpportunityRepository`, `ProductBriefingRepository` |
| `src/domain/entities/niche.py` | Modified | Agrega `discovery_mode` |
| `src/application/use_cases/` | New | `RunProductDiscoveryUseCase`, `GetProductBriefingUseCase` |
| `src/infrastructure/adapters/` | New + Modified | `FrustrationSignalAdapter`, `SerpAdapter` extendido |
| `src/infrastructure/adapters/claude_product_discovery.py` | New | Claude adapter para ProductDiscoveryPort |
| `src/infrastructure/db/models.py` | Modified | `ProductBriefingModel`, `ProductOpportunityModel`, `discovery_mode` en `NicheModel` |
| `src/api/routes/product_briefing.py` | New | `GET /product-briefing/{niche_id}` |
| `alembic/versions/` | New | Migración: 2 tablas nuevas + columna en niches |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| FrustrationSignalAdapter trae ruido (señales irrelevantes) | Med | Query patterns conservadores + umbral mínimo de señales |
| Claude clasifica mal el ProductType sin suficiente contexto | Med | Prompt con ejemplos concretos por tipo + fallback a "digital-product" |
| Migración rompe schema existente | Low | Solo tablas nuevas + 1 columna nullable en niches |

## Rollback Plan

- Tablas nuevas: `alembic downgrade` elimina `product_briefings` y `product_opportunities`
- Columna `discovery_mode` en niches: nullable con default "content" → no rompe nada al hacer downgrade
- Revert del commit no afecta el flujo de content opportunities

## Dependencies

- Mismo `ANTHROPIC_API_KEY` existente
- Reddit + HN APIs ya configuradas
- SerpAPI key existente

## Success Criteria

- [ ] `RunProductDiscoveryUseCase` ejecuta end-to-end para 1 nicho en modo "product"
- [ ] `ProfitabilityScore` calculado para ≥ 5 topics por nicho
- [ ] Cada `ProductOpportunity` tiene `ProductType` asignado y `product_reasoning` no vacío
- [ ] `GET /product-briefing/{niche_id}` retorna top 5 por `profitability_score`
- [ ] Flujo de content opportunities existente no se rompe (tests verdes)
- [ ] ADR documenta la separación de dominios

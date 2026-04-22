# Proposal: Opportunity Radar

## Intent

Creators e indie makers no tienen visibilidad sobre qué topics tienen alta demanda y baja competencia en su nicho. Las herramientas existentes (Semrush, Ahrefs) dan datos crudos sin síntesis accionable. Opportunity Radar resuelve esto generando un score de oportunidad por topic con una acción recomendada concreta, entregado como briefing semanal.

## Scope

### In Scope
- API REST para configurar nichos y consultar oportunidades
- Pipeline semanal: recolección → scoring → briefing
- 6 fuentes de datos: Google Trends, Reddit, HN, YouTube, Product Hunt, SerpAPI
- Scoring engine con 4 dimensiones normalizadas (0–100)
- Claude API genera insights y acciones recomendadas
- Briefing: top 10 oportunidades + acción por cada una
- Persistencia: SQLite (dev) → Postgres (prod)

### Out of Scope
- UI/frontend (primera versión API-only)
- Email delivery (fase 2)
- Alertas en tiempo real (fase 3)
- Google Ads Keyword Planner (requiere cuenta aprobada, se agrega después)
- Multi-tenant / auth complejo (fase 2)

## Approach

Clean Architecture con Ports & Adapters. Cada fuente de datos es un adapter independiente que implementa `TrendDataPort`. El `ScoringEngine` (application layer) orquesta la recolección en paralelo (asyncio), normaliza las señales y delega a Claude API para síntesis. APScheduler ejecuta el pipeline semanalmente.

```
API (FastAPI) → Use Cases → Domain Ports ← Infrastructure Adapters
                                              (pytrends, praw, httpx, anthropic)
```

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/domain/` | New | Entidades, ports, value objects del dominio |
| `src/application/` | New | Use cases: ScoreOpportunities, GenerateBriefing |
| `src/infrastructure/adapters/` | New | 6 adapters de fuentes + Claude adapter |
| `src/infrastructure/db/` | New | SQLAlchemy repos + migraciones Alembic |
| `src/infrastructure/scheduler/` | New | APScheduler pipeline semanal |
| `src/api/routes/` | New | Endpoints REST: /niches, /opportunities, /briefing |
| `docs/adr/` | New | ADRs para decisiones de arquitectura |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `pytrends` se rompe (no oficial) | Med | Abstracción detrás de port; fácil de swappear |
| Rate limits en Reddit/YouTube | Med | Caching agresivo + backoff exponencial |
| Costo Claude API escala | Med | Prompt caching + Batch API para scoring masivo |
| SerpAPI quota insuficiente | Low | Tier de pago disponible; fallback a resultados orgánicos |

## Rollback Plan

- Cada adapter es independiente: deshabilitar uno no rompe el sistema
- Migraciones Alembic tienen `downgrade()`
- Sin deploy en infra compartida en fase inicial → rollback = revert del commit

## Dependencies

- `uv` para gestión de dependencias
- Cuenta SerpAPI (100 búsquedas/mes gratis)
- `ANTHROPIC_API_KEY` en env
- Reddit API credentials (praw)
- YouTube Data API key

## Success Criteria

- [ ] Pipeline semanal ejecuta end-to-end sin errores para 1 nicho configurado
- [ ] Score generado para ≥ 10 topics por nicho
- [ ] Briefing retorna top 10 con acción recomendada por cada uno
- [ ] Todos los adapters tienen tests de integración contra APIs reales (con fixtures)
- [ ] API documentada en `/docs` (FastAPI auto-docs)

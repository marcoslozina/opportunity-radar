# Design: Opportunity Radar

## Technical Approach

Clean Architecture con Ports & Adapters. El dominio no conoce ninguna librería externa. Cada fuente de datos es un adapter independiente. El pipeline corre async con asyncio.gather(). Claude API sintetiza el score final y genera las acciones recomendadas.

---

## Architecture Decisions

| Decisión | Elegido | Descartado | Razón |
|---|---|---|---|
| Web framework | FastAPI | Flask / aiohttp | Async nativo, Pydantic v2, OpenAPI gratis |
| Scheduler | APScheduler (embedded) | Celery + Redis | Sin infra extra para MVP; migrable después |
| ORM | SQLAlchemy 2.0 async | SQLModel / raw | Async nativo, Alembic, flexible |
| DB dev/prod | SQLite → Postgres | Solo Postgres | Dev sin Docker; prod con Postgres vía env var |
| Collectors concurrencia | asyncio.gather() | ThreadPoolExecutor | IO-bound, async nativo, más limpio |
| Scoring synthesis | Claude API (Sonnet 4.6) | Reglas fijas | Genera acciones en lenguaje natural; prompt caching reduce costo |
| Caching API responses | TTLCache (cachetools) in-memory | Redis | Sin infra extra en fase 1; swappeable vía port |
| Normalización scores | Min-max per source + weighted avg | ML model | Determinístico, auditable, sin entrenamiento |

---

## Data Flow

```
POST /niches
     │
     ▼
CreateNicheUseCase ──→ NicheRepository (SQLAlchemy)

APScheduler (weekly)
     │
     ▼
RunPipelineUseCase
     │
     ├── asyncio.gather(
     │     GoogleTrendsAdapter,
     │     RedditAdapter,
     │     HackerNewsAdapter,
     │     YouTubeAdapter,
     │     ProductHuntAdapter,
     │     SerpAdapter
     │   )  ──→ List[TrendSignal]
     │
     ├── ScoringEngine.score(signals)
     │     └── normaliza dimensiones → OpportunityScore
     │
     ├── ClaudeInsightAdapter.synthesize(opportunities)
     │     └── genera recommended_action por oportunidad
     │
     └── BriefingRepository.save(briefing)

GET /briefing/{niche_id}
     │
     ▼
GetBriefingUseCase ──→ BriefingRepository.get_latest(niche_id)
```

---

## File Changes

| Archivo | Acción | Descripción |
|---|---|---|
| `src/domain/entities/niche.py` | Create | Dataclass Niche con id, name, keywords |
| `src/domain/entities/opportunity.py` | Create | Dataclass Opportunity + OpportunityScore VO |
| `src/domain/entities/briefing.py` | Create | Dataclass Briefing con lista de opportunities |
| `src/domain/ports/trend_data_port.py` | Create | ABC TrendDataPort → collect(keywords) → List[TrendSignal] |
| `src/domain/ports/insight_port.py` | Create | ABC InsightPort → synthesize(opportunities) → List[str] |
| `src/domain/ports/repository_ports.py` | Create | ABC NicheRepo, OpportunityRepo, BriefingRepo |
| `src/application/use_cases/run_pipeline.py` | Create | Orquesta collect → score → insight → save |
| `src/application/use_cases/get_briefing.py` | Create | Retorna último briefing para un nicho |
| `src/application/services/scoring_engine.py` | Create | Normaliza signals → OpportunityScore |
| `src/infrastructure/adapters/google_trends.py` | Create | pytrends adapter |
| `src/infrastructure/adapters/reddit.py` | Create | praw adapter |
| `src/infrastructure/adapters/hacker_news.py` | Create | httpx → HN API |
| `src/infrastructure/adapters/youtube.py` | Create | google-api-python-client adapter |
| `src/infrastructure/adapters/product_hunt.py` | Create | httpx → GraphQL adapter |
| `src/infrastructure/adapters/serp.py` | Create | serpapi adapter |
| `src/infrastructure/adapters/claude_insight.py` | Create | anthropic SDK adapter con prompt caching |
| `src/infrastructure/db/models.py` | Create | SQLAlchemy ORM models |
| `src/infrastructure/db/repositories.py` | Create | Implementaciones concretas de repos |
| `src/infrastructure/scheduler/pipeline_scheduler.py` | Create | APScheduler setup, lifespan FastAPI |
| `src/api/routes/niches.py` | Create | POST/GET/DELETE /niches |
| `src/api/routes/opportunities.py` | Create | GET /opportunities?niche_id= |
| `src/api/routes/briefing.py` | Create | GET /briefing/{niche_id} |
| `src/api/routes/health.py` | Create | GET /health |
| `src/main.py` | Create | FastAPI app factory + DI wiring |
| `alembic/` | Create | Migraciones DB |
| `pyproject.toml` | Create | uv project config |
| `docs/adr/ADR-001-clean-architecture.md` | Create | ADR arquitectura base |

---

## Interfaces / Contracts

```python
# TrendDataPort
class TrendDataPort(ABC):
    @abstractmethod
    async def collect(self, keywords: list[str]) -> list[TrendSignal]: ...

# TrendSignal (value object)
@dataclass(frozen=True)
class TrendSignal:
    source: str           # "google_trends" | "reddit" | ...
    topic: str
    raw_value: float      # 0.0–1.0 normalizado por el adapter
    signal_type: str      # "trend_velocity" | "social_signal" | ...
    collected_at: datetime

# OpportunityScore (value object)
@dataclass(frozen=True)
class OpportunityScore:
    trend_velocity: float      # 0–10
    competition_gap: float     # 0–10
    social_signal: float       # 0–10
    monetization_intent: float # 0–10
    total: float               # 0–100
    confidence: str            # "high" | "medium" | "low"
```

---

## Testing Strategy

| Capa | Qué testear | Approach |
|---|---|---|
| Domain | Cálculo de scores, validaciones de entidades | pytest puro, sin mocks |
| Application | RunPipelineUseCase, GetBriefingUseCase | Fake repos + fake adapters |
| Infrastructure | Cada adapter contra API real | pytest + fixtures grabadas (VCR/respx) |
| API | Endpoints REST | TestClient de FastAPI |

---

## Migration / Rollout

1. `uv init` + estructura de capas vacía
2. Dominio + ports (sin infra)
3. Adapters de a uno, con tests
4. Scoring engine + use cases
5. API + scheduler
6. Alembic migrations

No requiere feature flags. Rollback = revert de commit.

---

## Open Questions

- [ ] ¿Product Hunt API requiere OAuth o solo API key pública?
- [ ] ¿El briefing persiste histórico o solo el último por nicho?

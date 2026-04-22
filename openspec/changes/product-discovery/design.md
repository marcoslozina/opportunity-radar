# Design: Product Discovery

## Technical Approach

Dominio completamente separado. `ProductOpportunity` y `ProductBriefing` son entidades independientes con su propio pipeline, ports, adapters y tablas DB. El único punto de contacto con el dominio existente es `Niche` (que gana `discovery_mode`) y `TrendDataPort` (que `FrustrationSignalAdapter` implementa, reutilizando el mismo contrato).

---

## Architecture Decisions

| Decisión | Elegido | Descartado | Razón |
|---|---|---|---|
| Separación de dominio | Entidades propias (ProductOpportunity, ProductBriefing) | Extender Opportunity con nullables | Concerns distintos, evolución independiente, sin code smell de nullables |
| FrustrationSignalAdapter | Implementa `TrendDataPort` existente | Port nuevo `FrustrationPort` | Mismo contrato de collect() → reutiliza el pipeline de recolección sin cambios |
| ProductType clasificación | Claude API (ProductDiscoveryPort) | Reglas hardcodeadas | Clasificación contextual, flexible, en lenguaje natural |
| discovery_mode en Niche | Campo `str` con default `"content"` | Tabla pivot separada | Simple, aditivo, no rompe nada existente |
| DB schema | 2 tablas nuevas, 1 columna nullable en niches | Nullable columns en opportunities | Tablas propias = dominio separado en DB también |
| Scheduler | Misma instancia APScheduler, jobs con prefijo `product_` | Scheduler separado | Sin infra extra; jobs son independientes por ID |

---

## Data Flow

```
Niche (discovery_mode = "product" | "both")
       │
       ▼
APScheduler → RunProductDiscoveryUseCase
       │
       ├── asyncio.gather(
       │     FrustrationSignalAdapter(Reddit),   → frustration_level
       │     FrustrationSignalAdapter(HN),       → frustration_level
       │     SerpProductAdapter,                 → competition_gap
       │     SerpAdapter (existing CPC signals), → willingness_to_pay
       │   )  ──→ List[TrendSignal]
       │
       ├── ProfitabilityScoringEngine.score(signals)
       │     └── normaliza 4 dims → ProfitabilityScore
       │
       ├── ProductDiscoveryPort.classify(product_opportunities)
       │     └── Claude → ProductType + reasoning + price_range
       │
       └── ProductBriefingRepository.save(product_briefing)

GET /product-briefing/{niche_id}
       │
       ▼
GetProductBriefingUseCase → ProductBriefingRepository.get_latest()
```

---

## File Changes

| Archivo | Acción | Descripción |
|---|---|---|
| `src/domain/entities/niche.py` | Modify | Agrega `discovery_mode: str = "content"` |
| `src/domain/value_objects/product_type.py` | Create | Enum `ProductType`: ebook, micro-saas, service, digital-product |
| `src/domain/value_objects/profitability_score.py` | Create | VO frozen `ProfitabilityScore` con 4 dims + total + confidence |
| `src/domain/entities/product_opportunity.py` | Create | `ProductOpportunity`: id, topic, score, product_type, reasoning, price_range |
| `src/domain/entities/product_briefing.py` | Create | `ProductBriefing`: id, niche_id, opportunities, generated_at; propiedad `top_5` |
| `src/domain/ports/product_discovery_port.py` | Create | ABC `ProductDiscoveryPort.classify(opportunities) -> list[ProductClassification]` |
| `src/domain/ports/product_repository_ports.py` | Create | ABCs `ProductOpportunityRepository`, `ProductBriefingRepository` |
| `src/application/services/profitability_scoring_engine.py` | Create | Normaliza signals → ProfitabilityScore por topic |
| `src/application/use_cases/run_product_discovery.py` | Create | Orquesta collect → score → classify → save |
| `src/application/use_cases/get_product_briefing.py` | Create | Retorna último ProductBriefing para un nicho |
| `src/infrastructure/adapters/frustration_signal.py` | Create | Reddit + HN con pain point query patterns |
| `src/infrastructure/adapters/serp_product.py` | Create | SerpAPI con queries "X tool/software/alternative" → competition_gap |
| `src/infrastructure/adapters/claude_product_discovery.py` | Create | Anthropic SDK → ProductType + reasoning + price_range |
| `src/infrastructure/db/models.py` | Modify | Agrega `ProductBriefingModel`, `ProductOpportunityModel`, `discovery_mode` en `NicheModel` |
| `src/infrastructure/db/product_repositories.py` | Create | SQLAlchemy impls de ProductOpportunityRepository y ProductBriefingRepository |
| `src/infrastructure/scheduler/pipeline_scheduler.py` | Modify | Agrega `add_product_discovery_job()` si `discovery_mode` incluye "product" |
| `src/api/routes/product_briefing.py` | Create | `GET /product-briefing/{niche_id}` → top 5 por profitability_score |
| `src/api/schemas/product_opportunity.py` | Create | Pydantic schemas: `ProductOpportunityResponse`, `ProductBriefingResponse` |
| `src/main.py` | Modify | Incluir router de product_briefing |
| `alembic/versions/` | Create | Migración: `product_briefings`, `product_opportunities`, `discovery_mode` en niches |

---

## Interfaces / Contracts

```python
# ProductType
from enum import Enum
class ProductType(str, Enum):
    EBOOK = "ebook"
    MICRO_SAAS = "micro-saas"
    SERVICE = "service"
    DIGITAL_PRODUCT = "digital-product"

# ProfitabilityScore (value object)
@dataclass(frozen=True)
class ProfitabilityScore:
    frustration_level: float    # 0–10
    market_size: float          # 0–10
    competition_gap: float      # 0–10
    willingness_to_pay: float   # 0–10
    total: float                # 0–100
    confidence: str             # "high" | "medium" | "low"

# ProductClassification (output de ProductDiscoveryPort)
@dataclass(frozen=True)
class ProductClassification:
    product_type: ProductType
    reasoning: str
    recommended_price_range: str  # ej: "$29–$49"

# ProductDiscoveryPort
class ProductDiscoveryPort(ABC):
    @abstractmethod
    async def classify(
        self, opportunities: list[ProductOpportunity]
    ) -> list[ProductClassification]: ...
```

---

## Testing Strategy

| Capa | Qué testear | Approach |
|---|---|---|
| Domain | ProfitabilityScore.from_dimensions(), ProductBriefing.top_5 | pytest puro |
| Application | RunProductDiscoveryUseCase (fallo de adapter, clasificación OK) | Fake repos + fake adapters |
| Infrastructure | FrustrationSignalAdapter (respx mock) | respx fixtures |
| API | GET /product-briefing 200 y 404 | TestClient FastAPI |

---

## Migration / Rollout

1. Migración Alembic aditiva: crea `product_briefings`, `product_opportunities`, agrega `discovery_mode VARCHAR(10) DEFAULT 'content'` en niches
2. Nichos existentes quedan con `discovery_mode = "content"` → sin cambio de comportamiento
3. No requiere backfill

## Open Questions

- [ ] ¿El `FrustrationSignalAdapter` busca en todos los subreddits o solo en `r/all`?
- [ ] ¿`recommended_price_range` en USD siempre o según el mercado del nicho?

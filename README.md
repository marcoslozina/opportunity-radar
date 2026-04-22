# Opportunity Radar

AI-powered opportunity scoring engine para creators e indie makers. Analiza tendencias, competencia y señales de monetización para encontrar los topics con mayor oportunidad en tu nicho — entregado como briefing semanal con acciones concretas.

---

## Qué hace

- Recolecta señales de 6 fuentes: Google Trends, Reddit, Hacker News, YouTube, Product Hunt, SerpAPI
- Calcula un **Opportunity Score** (0–100) por topic con 4 dimensiones
- Usa Claude API para generar una **acción recomendada** por oportunidad
- Entrega un **briefing semanal** con el top 10 de tu nicho

```
Niche + Keywords
       │
       ▼
asyncio.gather(6 collectors)
       │
       ▼
ScoringEngine → OpportunityScore por topic
       │
       ▼
Claude API → recommended_action por oportunidad
       │
       ▼
Briefing: top 10 oportunidades + acción
```

---

## Setup local

### Requisitos

- Python 3.12+
- [uv](https://astral.sh/uv)

### Instalación

```bash
# 1. Clonar e instalar deps
git clone https://github.com/marcoslozina/opportunity-radar
cd opportunity-radar
uv sync

# 2. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus API keys

# 3. Correr migraciones
PYTHONPATH=src uv run alembic upgrade head

# 4. Levantar el servidor
PYTHONPATH=src uv run uvicorn src.main:app --reload
```

API disponible en `http://localhost:8000` — docs en `http://localhost:8000/docs`

---

## Variables de entorno

| Variable | Requerida | Default | Descripción |
|---|---|---|---|
| `DATABASE_URL` | No | `sqlite+aiosqlite:///./opportunity_radar.db` | URL de la DB |
| `ANTHROPIC_API_KEY` | **Sí** | — | API key de Anthropic |
| `PIPELINE_SCHEDULE` | No | `0 8 * * 1` | Cron del pipeline semanal (lunes 08:00 UTC) |
| `REDDIT_CLIENT_ID` | No | — | App ID de Reddit |
| `REDDIT_CLIENT_SECRET` | No | — | App secret de Reddit |
| `YOUTUBE_API_KEY` | No | — | Google Cloud API key con YouTube Data API v3 |
| `SERP_API_KEY` | No | — | API key de SerpAPI |
| `PRODUCT_HUNT_TOKEN` | No | — | API token de Product Hunt |

Las fuentes sin credenciales se omiten silenciosamente — el pipeline continúa con las disponibles.

---

## Uso básico

### Crear un nicho

```bash
curl -X POST http://localhost:8000/niches \
  -H "Content-Type: application/json" \
  -d '{"name": "Angular", "keywords": ["angular signals", "angular 17", "standalone components"]}'
```

### Ver el briefing semanal

```bash
curl http://localhost:8000/briefing/{niche_id}
```

### Respuesta

```json
{
  "id": "...",
  "niche_id": "...",
  "generated_at": "2026-04-22T08:00:00",
  "opportunities": [
    {
      "topic": "angular signals",
      "score": {
        "trend_velocity": 8.0,
        "competition_gap": 7.0,
        "social_signal": 6.0,
        "monetization_intent": 9.0,
        "total": 75.5,
        "confidence": "high"
      },
      "recommended_action": "Publicar tutorial avanzado de Signals antes del jueves"
    }
  ]
}
```

---

## Tests

```bash
# Unit tests
PYTHONPATH=src uv run pytest tests/unit/ -v

# Integration tests
PYTHONPATH=src uv run pytest tests/integration/ -v

# Todos
PYTHONPATH=src uv run pytest -v
```

---

## Arquitectura

```
src/
  domain/           # entidades, ports, value objects — sin deps externas
  application/      # use cases, scoring engine
  infrastructure/   # adapters (APIs), DB (SQLAlchemy), scheduler (APScheduler)
  api/              # FastAPI routes, schemas Pydantic, middleware
  config.py         # pydantic-settings
```

Decisiones de arquitectura documentadas en [`docs/adr/`](docs/adr/).

---

## Pipeline manual

Para disparar el pipeline de un nicho sin esperar el scheduler:

```python
# desde una shell Python con PYTHONPATH=src
import asyncio
from uuid import UUID
from infrastructure.db.session import AsyncSessionFactory
from infrastructure.db.repositories import SQLNicheRepository, SQLBriefingRepository
from infrastructure.adapters.hacker_news import HackerNewsAdapter
from infrastructure.adapters.claude_insight import ClaudeInsightAdapter
from application.services.scoring_engine import ScoringEngine
from application.use_cases.run_pipeline import RunPipelineUseCase
from domain.entities.niche import NicheId

async def run(niche_id: str):
    async with AsyncSessionFactory() as session:
        use_case = RunPipelineUseCase(
            niche_repo=SQLNicheRepository(session),
            briefing_repo=SQLBriefingRepository(session),
            collectors=[HackerNewsAdapter()],
            insight_port=ClaudeInsightAdapter(),
            scoring_engine=ScoringEngine(),
        )
        await use_case.execute(NicheId(UUID(niche_id)))

asyncio.run(run("tu-niche-id"))
```

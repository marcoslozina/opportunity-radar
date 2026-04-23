# Opportunity Radar

AI-powered opportunity scoring engine para creators e indie makers. Analiza tendencias, competencia y señales de monetización para encontrar los topics con mayor oportunidad — entregado como briefing semanal con acciones concretas.

Incluye dos modos de análisis:
- **Content** — encontrá sobre qué crear contenido (top 10 por Opportunity Score)
- **Product** — encontrá qué producto construir y cuánto cobrar (top 5 por Profitability Score)

---

## Cómo funciona

```
Categoría → Claude sugiere nichos → Claude genera keywords
                     │
                     ▼
         asyncio.gather(6 collectors)
         ├── HackerNews        → social_signal / frustration_level
         ├── Reddit            → social_signal / frustration_level
         ├── Google Trends     → trend_velocity
         ├── YouTube           → social_signal
         ├── SerpAPI           → competition_gap + monetization_intent
         └── Product Hunt      → monetization_intent
                     │
                     ▼
         ScoringEngine / ProfitabilityScoringEngine
                     │
                     ▼
         Claude → recommended_action / ProductType + price_range
                     │
                     ▼
         Briefing: top 10 content + top 5 product opportunities
```

---

## Setup local

### Requisitos

- Python 3.12+
- [uv](https://astral.sh/uv)

### Instalación

```bash
git clone https://github.com/marcoslozina/opportunity-radar
cd opportunity-radar
uv sync
```

### Variables de entorno

Crear `.env` en la raíz del proyecto:

```
# Obligatorio
ANTHROPIC_API_KEY=sk-ant-api03-...

# Opcional — sin credenciales el adapter se omite silenciosamente
DATABASE_URL=sqlite+aiosqlite:///./opportunity_radar.db
PIPELINE_SCHEDULE=0 8 * * 1

REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=

YOUTUBE_API_KEY=
SERP_API_KEY=
PRODUCT_HUNT_TOKEN=
```

### Migraciones y servidor

```bash
make migrate   # aplica migraciones Alembic
make dev       # levanta el backend en http://localhost:8000
make dash      # levanta el dashboard en http://localhost:8501
```

---

## Uso

### Dashboard (recomendado)

```bash
make dev    # terminal 1
make dash   # terminal 2
```

Abrí `http://localhost:8501`. El flujo completo:

1. **Elegís una categoría** — Dev Tools, IA, Marketing, etc.
2. **Claude sugiere 6 nichos rentables** con contexto de por qué tienen potencial
3. **Elegís un nicho** → Claude genera keywords sugeridas automáticamente
4. **Seleccionás keywords** con checkboxes, agregás las tuyas, elegís modo (content / product / both)
5. **Crear nicho** → el scheduler lo analiza cada lunes a las 08:00 UTC
6. **Correr ahora** → botón "▶ Correr pipeline ahora" en el dashboard (sin esperar el scheduler)

### API directa

```bash
# Crear nicho
curl -X POST http://localhost:8000/niches \
  -H "Content-Type: application/json" \
  -d '{"name": "Angular", "keywords": ["angular signals", "angular 17"], "discovery_mode": "both"}'

# Correr pipeline manualmente
make run-pipeline niche=<niche-id>
make run-content  niche=<niche-id>
make run-product  niche=<niche-id>

# Ver briefings
curl http://localhost:8000/briefing/<niche-id>
curl http://localhost:8000/product-briefing/<niche-id>
```

---

## Comandos

```bash
make dev           # backend (uvicorn --reload)
make dash          # dashboard Streamlit
make migrate       # alembic upgrade head

make run-pipeline niche=<uuid>   # content + product
make run-content  niche=<uuid>   # solo content
make run-product  niche=<uuid>   # solo product

make test          # lint + unit + integration
make test-unit     # solo tests/unit/
make test-int      # solo tests/integration/

make lint          # ruff check
make format        # ruff format
make typecheck     # mypy
make clean         # limpia __pycache__, .pytest_cache, etc.
```

---

## Arquitectura

```
src/
  domain/           # entidades, ports, value objects — sin deps externas
  application/      # use cases, scoring engines
  infrastructure/   # adapters (APIs), DB (SQLAlchemy), scheduler (APScheduler)
  api/              # FastAPI routes, schemas Pydantic, middleware
  config.py         # pydantic-settings
dashboard.py        # Streamlit dashboard
```

Decisiones de arquitectura documentadas en [`docs/adr/`](docs/adr/).

---

## Tests

```bash
make test
# o individualmente:
PYTHONPATH=src uv run pytest tests/unit/ -v
PYTHONPATH=src uv run pytest tests/integration/ -v
```

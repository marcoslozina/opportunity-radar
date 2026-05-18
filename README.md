# Opportunity Radar

[![Python](https://img.shields.io/badge/python-3.12%2B-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-orange)](https://sqlalchemy.org)
[![CI](https://github.com/marcoslozina/opportunity-radar/actions/workflows/ci.yml/badge.svg)](https://github.com/marcoslozina/opportunity-radar/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

AI-powered opportunity scoring engine for creators and indie makers. Analyzes trends, competition, frustration signals, and monetization intent across 6 data sources to surface the highest-potential topics — delivered as a weekly briefing with concrete, executable actions.

---

## What problem does it solve

Creators and indie makers waste hours manually researching what to build or write about. They check Reddit, Hacker News, Google Trends, and YouTube separately — then have no systematic way to compare or rank opportunities.

**Opportunity Radar automates the entire discovery pipeline:**
- Collects signals from 6 sources simultaneously
- Scores every topic across 5 dimensions using a weighted model
- Runs Claude to generate a concrete, one-week-executable action per opportunity
- Delivers a ranked briefing (top 10 content + top 5 product opportunities)

---

## How it works

```
Niche + keywords
      │
      ▼
asyncio.gather(6 collectors in parallel)
├── HackerNews     → social_signal + frustration_level
├── Reddit         → social_signal + frustration_level
├── Google Trends  → trend_velocity
├── YouTube        → social_signal
├── SerpAPI        → competition_gap + monetization_intent
└── Product Hunt   → monetization_intent
      │
      ▼
ScoringEngine (weighted, per discovery_mode)
      │
      ├── content mode  → trend_velocity 30%, competition_gap 25%,
      │                   social_signal 20%, monetization_intent 25%
      ├── real_estate   → monetization_intent 30%, frustration_level 20%
      └── esg           → competition_gap 30%, frustration_level 25%
      │
      ▼
Claude (claude-3-5-sonnet) → recommended_action per opportunity
      │
      ▼
Briefing: top 10 content opportunities
      │
      ▼
ProfitabilityScoringEngine → top 5 product opportunities
      │
      ▼
Claude (claude-sonnet-4-6) → product_type + price_range
      │
      ▼
Persisted to DB + ContentForge /api/v1/feed
```

---

## Features

| Feature | Description |
|---------|-------------|
| Multi-source collection | HackerNews, Reddit, Google Trends, YouTube, SerpAPI, Product Hunt |
| Multi-mode scoring | `content`, `product`, `real_estate`, `esg_intelligence` |
| AI-powered actions | Claude generates a concrete 15-word action per opportunity |
| Product classification | Claude classifies each product as ebook / micro-saas / service / digital-product |
| Scheduled pipeline | APScheduler runs the full pipeline weekly (configurable cron) |
| Alert rules | Webhook + email alerts when opportunities exceed a score threshold |
| API key auth | SHA-256 hashed keys with TTL cache, tier-based quota enforcement |
| Rate limiting | Per-IP and per-API-key via slowapi |
| ContentForge feed | `/api/v1/feed` exposes opportunities to the ContentForge /ideas dashboard |
| Billing | Lemon Squeezy checkout + webhook provisioning |

---

## Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI 0.136+ |
| ORM | SQLAlchemy 2.0 async |
| Database | PostgreSQL (production) / SQLite (dev/test) |
| Migrations | Alembic |
| Scheduler | APScheduler (embedded) |
| AI | Anthropic Claude API |
| Cache | Redis (rate-limiting + quota) |
| Auth | API key + Supabase JWT |
| Email | Resend |
| Billing | Lemon Squeezy |
| Dashboard | Streamlit |
| Error tracking | Sentry |

---

## Project structure

```
src/
  domain/
    entities/          # Opportunity, Briefing, Niche, AlertRule, ApiKey
    ports/             # Abstract interfaces (TrendDataPort, InsightPort, ...)
    value_objects/     # OpportunityScore, TrendSignal, EvidenceItem, ...
  application/
    use_cases/         # RunPipelineUseCase, RunProductDiscoveryUseCase, GetBriefingUseCase
    services/          # ScoringEngine, ProfitabilityScoringEngine, TrajectoryService
  infrastructure/
    adapters/          # HackerNews, Reddit, GoogleTrends, YouTube, Serp, Claude, ...
    db/                # SQLAlchemy models, repositories, session
    scheduler/         # APScheduler pipeline_scheduler
    billing/           # Lemon Squeezy checkout + webhook handler
  api/
    routes/            # FastAPI routers (health, niches, briefing, contentforge, ...)
    schemas/           # Pydantic request/response models
    middleware/        # Auth, rate-limiting, logging, request-id
    dependencies/      # API key resolution + quota enforcement
  config.py            # pydantic-settings (reads from .env)
dashboard.py           # Streamlit dashboard
alembic/               # DB migration scripts
tests/
  unit/
  integration/
```

---

## Quickstart

### Requirements

- Python 3.12+
- [uv](https://astral.sh/uv)
- PostgreSQL (or SQLite for local dev)

### Installation

```bash
git clone https://github.com/marcoslozina/opportunity-radar
cd opportunity-radar
uv sync
```

### Environment variables

Copy `.env.example` to `.env` and fill in values:

```bash
cp .env.example .env
```

Required:

```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/radar
```

Optional (adapters skip silently if not set):

```
ANTHROPIC_API_KEY=sk-ant-...
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
YOUTUBE_API_KEY=
SERP_API_KEY=
PRODUCT_HUNT_TOKEN=
RESEND_API_KEY=
SENTRY_DSN=
REDIS_URL=redis://localhost:6379
```

### Migrations and server

```bash
make migrate    # alembic upgrade head
make dev        # uvicorn src/main.py:app --reload  (http://localhost:8000)
make dash       # Streamlit dashboard (http://localhost:8501)
```

---

## Development

### Lint

```bash
uv run ruff check .
uv run ruff check . --fix   # auto-fix safe issues
```

### Tests

```bash
uv run pytest tests/unit/ -v
uv run pytest tests/integration/ -v
```

### Dependency audit

```bash
uvx pip-audit
```

### Type check

```bash
uv run mypy src/
```

---

## API reference

### Core endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | none | Health check — returns `{"status", "version", "database", "redis", "scheduler"}` |
| `POST` | `/niches` | API key | Create a new niche |
| `GET` | `/niches` | API key | List active niches |
| `DELETE` | `/niches/{id}` | API key | Delete a niche |
| `GET` | `/briefing/{niche_id}` | API key | Get latest briefing with trajectory + DNA |
| `GET` | `/opportunities?niche_id=` | API key | Paginated opportunity list |
| `POST` | `/pipeline/run/{niche_id}` | none | Trigger pipeline manually (`mode=content|product|both`) |

### ContentForge endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/feed?limit=N` | none | Top opportunities feed for ContentForge /ideas dashboard |
| `POST` | `/api/v1/notify` | none | Accept inbound event notifications from ContentForge |

---

## ContentForge integration

Opportunity Radar is a data producer for the ContentForge platform. The ContentForge `/ideas` dashboard polls `/api/v1/feed` to display the latest high-scoring opportunities across all tracked niches.

### Data flow

```
ContentForge /ideas dashboard
          │
          │  GET /api/v1/feed?limit=20
          ▼
Opportunity Radar API
          │
          │  SELECT top opportunities
          │  JOIN briefings, niches
          │  ORDER BY total DESC
          ▼
Feed items:
  {
    "id":           "uuid",
    "title":        "topic string",
    "summary":      "Claude-generated recommended action",
    "url":          "/briefing/{niche_id}",
    "product":      "opportunity-radar",
    "tags":         ["niche_name", "confidence", "domain_applicability?"],
    "published_at": "2025-01-01T08:00:00"
  }
```

### ContentForge API contract

| Endpoint | Response | Notes |
|----------|----------|-------|
| `GET /health` | `{"status": "ok"\|"degraded", "version": "x.y.z"}` | Status 200 or 503 |
| `GET /api/v1/feed?limit=N` | `{"items": [...]}` | Each item has `id, title, summary, url, product, tags, published_at` |
| `POST /api/v1/notify` | `{"status": "ok", "event": "..."}` | Accepts any JSON event payload |

---

## Status

| Component | Status |
|-----------|--------|
| Content pipeline | Production |
| Product discovery pipeline | Production |
| Alert rules (webhook + email) | Production |
| Billing (Lemon Squeezy) | Production |
| ContentForge feed | Production |
| Dashboard (Streamlit) | Production |
| Multi-tenant API keys | Production |
| Tier-based quota | Production |

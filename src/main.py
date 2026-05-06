from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.middleware.limiter import limiter
from api.middleware.logging import RequestLoggingMiddleware
from api.routes import alert_rules, billing, briefing, health, keywords, niches, opportunities, pipeline, product_briefing
from api.routes.keywords import niches_router as niches_suggest_router
from infrastructure.scheduler.pipeline_scheduler import schedule_all_niches, scheduler

logging.basicConfig(level=logging.INFO)

# ── Sentry ────────────────────────────────────────────────────────────────────
SENTRY_DSN = os.getenv("SENTRY_DSN", "")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=0.05,
        environment=os.getenv("ENVIRONMENT", "production"),
        send_default_pii=False,
    )

# ── Startup validation ────────────────────────────────────────────────────────
REQUIRED = ["DATABASE_URL"]
RECOMMENDED = ["REDIS_URL", "LS_API_KEY", "SENTRY_DSN"]

missing_required = [k for k in REQUIRED if not os.getenv(k)]
if missing_required:
    raise RuntimeError(f"Missing required env vars: {', '.join(missing_required)}")

missing_recommended = [k for k in RECOMMENDED if not os.getenv(k)]
if missing_recommended:
    logging.warning(
        f"[STARTUP] Optional vars not set (some features disabled): {', '.join(missing_recommended)}"
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    scheduler.start()
    await schedule_all_niches()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="Opportunity Radar",
    description="AI-powered opportunity scoring engine for creators and indie makers",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(health.router)
app.include_router(niches.router)
app.include_router(opportunities.router)
app.include_router(briefing.router)
app.include_router(product_briefing.router)
app.include_router(keywords.router)
app.include_router(niches_suggest_router)
app.include_router(pipeline.router)
app.include_router(alert_rules.router)
app.include_router(billing.router)

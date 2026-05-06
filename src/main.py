from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.middleware.logging import RequestLoggingMiddleware
from api.routes import alert_rules, briefing, health, keywords, niches, opportunities, pipeline, product_briefing
from api.routes.keywords import niches_router as niches_suggest_router
from infrastructure.scheduler.pipeline_scheduler import schedule_all_niches, scheduler

logging.basicConfig(level=logging.INFO)


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

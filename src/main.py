from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.middleware.logging import RequestLoggingMiddleware
from api.routes import briefing, health, niches, opportunities
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

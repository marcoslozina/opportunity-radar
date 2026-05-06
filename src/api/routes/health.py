from __future__ import annotations

import sqlalchemy
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.db.session import get_session
from infrastructure.quota import get_redis

router = APIRouter()


@router.get("/health")
async def health(session: AsyncSession = Depends(get_session)) -> JSONResponse:
    from infrastructure.scheduler.pipeline_scheduler import scheduler

    checks: dict[str, str] = {"status": "ok"}

    # Scheduler
    checks["scheduler"] = "running" if scheduler.running else "stopped"

    # Database
    try:
        await session.execute(sqlalchemy.text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {str(e)[:50]}"
        checks["status"] = "degraded"

    # Redis
    r = await get_redis()
    checks["redis"] = "ok" if r is not None else "unavailable"

    status_code = 200 if checks["status"] == "ok" else 503
    return JSONResponse(content=checks, status_code=status_code)

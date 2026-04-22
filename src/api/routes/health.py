from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    scheduler: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    from infrastructure.scheduler.pipeline_scheduler import scheduler

    scheduler_status = "running" if scheduler.running else "stopped"
    return HealthResponse(status="ok", scheduler=scheduler_status)

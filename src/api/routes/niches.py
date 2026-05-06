from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.api_key import get_api_key
from api.middleware.limiter import limiter
from api.middleware.rate_limits import get_rate_limit
from api.schemas.niche import CreateNicheRequest, NicheResponse
from application.use_cases.create_niche import CreateNicheUseCase, KeywordsRequiredError
from domain.entities.niche import NicheId
from domain.value_objects.api_key_context import ApiKeyContext
from infrastructure.db.repositories import SQLNicheRepository
from infrastructure.db.session import get_session
from infrastructure.scheduler.pipeline_scheduler import add_niche_job, add_product_discovery_job, remove_niche_job

from uuid import UUID

router = APIRouter(prefix="/niches", tags=["niches"])


@router.post("", response_model=NicheResponse, status_code=201)
async def create_niche(
    body: CreateNicheRequest,
    session: AsyncSession = Depends(get_session),
) -> NicheResponse:
    repo = SQLNicheRepository(session)
    use_case = CreateNicheUseCase(repo)
    try:
        niche = await use_case.execute(
            name=body.name,
            keywords=body.keywords,
            discovery_mode=body.discovery_mode,
        )
    except KeywordsRequiredError as exc:
        raise HTTPException(status_code=422, detail={"code": "KEYWORDS_REQUIRED", "message": str(exc)})

    add_niche_job(str(niche.id))
    if niche.discovery_mode in ("product", "both"):
        add_product_discovery_job(niche)
    return NicheResponse(
        id=str(niche.id),
        name=niche.name,
        keywords=niche.keywords,
        active=niche.active,
        discovery_mode=niche.discovery_mode,
    )


@router.get("", response_model=list[NicheResponse])
@limiter.limit(get_rate_limit)
async def list_niches(
    request: Request,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    ctx: ApiKeyContext = Depends(get_api_key),
    session: AsyncSession = Depends(get_session),
) -> list[NicheResponse]:
    repo = SQLNicheRepository(session)
    niches = await repo.find_all_active(limit=limit, offset=offset)
    return [
        NicheResponse(id=str(n.id), name=n.name, keywords=n.keywords, active=n.active, discovery_mode=n.discovery_mode)
        for n in niches
    ]


@router.delete("/{niche_id}", status_code=204)
async def delete_niche(
    niche_id: str,
    session: AsyncSession = Depends(get_session),
) -> Response:
    repo = SQLNicheRepository(session)
    niche = await repo.find_by_id(NicheId(UUID(niche_id)))
    if niche is None:
        raise HTTPException(status_code=404, detail="Niche not found")
    await repo.delete(NicheId(UUID(niche_id)))
    remove_niche_job(niche_id)
    return Response(status_code=204)

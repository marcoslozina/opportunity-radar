from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.api_key import get_api_key
from api.middleware.limiter import limiter
from api.middleware.rate_limits import get_rate_limit
from api.schemas.alert_rule import AlertRuleResponse, CreateAlertRuleRequest
from domain.entities.alert_rule import AlertRule, AlertRuleId
from domain.value_objects.api_key_context import ApiKeyContext
from infrastructure.db.repositories import SqlAlertRuleRepository, SQLNicheRepository
from infrastructure.db.session import get_session

router = APIRouter(prefix="/alert-rules", tags=["alert-rules"])


def _to_response(rule: AlertRule) -> AlertRuleResponse:
    return AlertRuleResponse(
        id=str(rule.id),
        niche_id=rule.niche_id,
        threshold_score=rule.threshold_score,
        delivery_channel=rule.delivery_channel,
        webhook_url=rule.webhook_url,
        email=rule.email,
        active=rule.active,
        last_notified_at=rule.last_notified_at,
        created_at=rule.created_at,
    )


@router.post("", response_model=AlertRuleResponse, status_code=201)
@limiter.limit(get_rate_limit)
async def create_alert_rule(
    request: Request,
    body: CreateAlertRuleRequest,
    session: AsyncSession = Depends(get_session),
    _: ApiKeyContext = Depends(get_api_key),
) -> AlertRuleResponse:
    # Validate niche exists
    niche_repo = SQLNicheRepository(session)
    from domain.entities.niche import NicheId

    try:
        niche_uuid = UUID(body.niche_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="niche_id must be a valid UUID")

    niche = await niche_repo.find_by_id(NicheId(niche_uuid))
    if niche is None:
        raise HTTPException(status_code=404, detail="Niche not found")

    rule = AlertRule.create(
        niche_id=body.niche_id,
        threshold_score=body.threshold_score,
        delivery_channel=body.delivery_channel,
        webhook_url=body.webhook_url,
        email=body.email,
    )

    repo = SqlAlertRuleRepository(session)
    async with session.begin():
        await repo.save(rule)

    return _to_response(rule)


@router.get("", response_model=list[AlertRuleResponse])
@limiter.limit(get_rate_limit)
async def list_alert_rules(
    request: Request,
    niche_id: str | None = None,
    session: AsyncSession = Depends(get_session),
    _: ApiKeyContext = Depends(get_api_key),
) -> list[AlertRuleResponse]:
    repo = SqlAlertRuleRepository(session)
    rules = await repo.list_all(niche_id=niche_id)
    return [_to_response(r) for r in rules]


@router.delete("/{rule_id}", status_code=204)
@limiter.limit(get_rate_limit)
async def delete_alert_rule(
    request: Request,
    rule_id: str,
    session: AsyncSession = Depends(get_session),
    _: ApiKeyContext = Depends(get_api_key),
) -> Response:
    try:
        rule_uuid = UUID(rule_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="rule_id must be a valid UUID")

    repo = SqlAlertRuleRepository(session)
    rule = await repo.find_by_id(AlertRuleId(rule_uuid))
    if rule is None:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    async with session.begin():
        await repo.deactivate(AlertRuleId(rule_uuid))
    return Response(status_code=204)

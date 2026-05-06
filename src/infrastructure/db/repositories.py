from __future__ import annotations

import dataclasses
import json
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.entities.alert_rule import AlertRule, AlertRuleId
from domain.entities.api_key import ApiKey
from domain.entities.briefing import Briefing, BriefingId
from domain.entities.niche import Niche, NicheId
from domain.entities.opportunity import Opportunity, OpportunityId
from domain.ports.repository_ports import AlertRuleRepository, ApiKeyRepository, BriefingRepository, NicheRepository, OpportunityRepository
from domain.value_objects.evidence_item import EvidenceItem
from domain.value_objects.opportunity_score import OpportunityScore
from infrastructure.db.models import AlertRuleModel, ApiKeyModel, BriefingModel, NicheModel, OpportunityModel


class SQLNicheRepository(NicheRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, niche: Niche) -> None:
        model = NicheModel(
            id=str(niche.id),
            name=niche.name,
            keywords_json=__import__("json").dumps(niche.keywords),
            active=niche.active,
            discovery_mode=niche.discovery_mode,
        )
        self._session.add(model)
        await self._session.commit()

    async def find_by_id(self, niche_id: NicheId) -> Niche | None:
        result = await self._session.get(NicheModel, str(niche_id))
        return _to_niche(result) if result else None

    async def find_all_active(self, limit: int = 50, offset: int = 0) -> list[Niche]:
        stmt = (
            select(NicheModel)
            .where(NicheModel.active.is_(True))
            .offset(offset)
            .limit(limit)
        )
        rows = await self._session.scalars(stmt)
        return [_to_niche(row) for row in rows]

    async def delete(self, niche_id: NicheId) -> None:
        stmt = delete(NicheModel).where(NicheModel.id == str(niche_id))
        await self._session.execute(stmt)
        await self._session.commit()


class SQLOpportunityRepository(OpportunityRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_bulk(self, opportunities: list[Opportunity], niche_id: NicheId) -> None:
        raise NotImplementedError("Use BriefingRepository.save to persist opportunities")

    async def find_by_niche(
        self, niche_id: NicheId, cursor: UUID | None = None, limit: int = 20
    ) -> list[Opportunity]:
        stmt = (
            select(OpportunityModel)
            .join(BriefingModel)
            .where(BriefingModel.niche_id == str(niche_id))
            .order_by(OpportunityModel.total.desc())
            .limit(limit)
        )
        if cursor:
            stmt = stmt.where(OpportunityModel.id > str(cursor))
        rows = await self._session.scalars(stmt)
        return [_to_opportunity(row) for row in rows]


class SQLBriefingRepository(BriefingRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, briefing: Briefing) -> None:
        model = BriefingModel(
            id=str(briefing.id),
            niche_id=str(briefing.niche_id),
            generated_at=briefing.generated_at,
        )
        for opp in briefing.opportunities:
            model.opportunities.append(
                OpportunityModel(
                    id=str(opp.id),
                    briefing_id=str(briefing.id),
                    topic=opp.topic,
                    trend_velocity=opp.score.trend_velocity,
                    competition_gap=opp.score.competition_gap,
                    social_signal=opp.score.social_signal,
                    monetization_intent=opp.score.monetization_intent,
                    frustration_level=opp.score.frustration_level,
                    total=opp.score.total,
                    confidence=opp.score.confidence,
                    recommended_action=opp.recommended_action,
                    domain_applicability=opp.domain_applicability,
                    domain_reasoning=opp.domain_reasoning,
                    evidence_json=_serialize_evidence(opp.evidence),
                )
            )
        self._session.add(model)
        await self._session.commit()

    async def get_latest(self, niche_id: NicheId) -> Briefing | None:
        stmt = (
            select(BriefingModel)
            .options(selectinload(BriefingModel.opportunities))
            .where(BriefingModel.niche_id == str(niche_id))
            .order_by(BriefingModel.generated_at.desc())
            .limit(1)
        )
        result = await self._session.scalar(stmt)
        return _to_briefing(result) if result else None

    async def get_previous(self, niche_id: NicheId) -> Briefing | None:
        stmt = (
            select(BriefingModel)
            .options(selectinload(BriefingModel.opportunities))
            .where(BriefingModel.niche_id == str(niche_id))
            .order_by(BriefingModel.generated_at.desc())
            .offset(1)
            .limit(1)
        )
        result = await self._session.scalar(stmt)
        return _to_briefing(result) if result else None


# --- evidence helpers ---

def _serialize_evidence(items: list[EvidenceItem]) -> str:
    return json.dumps([
        {**dataclasses.asdict(e), "collected_at": e.collected_at.isoformat()}
        for e in items
    ])


def _deserialize_evidence(raw: str) -> list[EvidenceItem]:
    try:
        items = json.loads(raw or "[]")
        return [
            EvidenceItem(
                **{**item, "collected_at": datetime.fromisoformat(item["collected_at"])}
            )
            for item in items
        ]
    except Exception as e:
        logging.error(
            f"[REPO] Failed to deserialize evidence: {e}. Raw value: {str(raw)[:200]}"
        )
        return []


# --- mappers ---

def _to_niche(model: NicheModel) -> Niche:
    return Niche(
        id=NicheId(UUID(model.id)),
        name=model.name,
        keywords=model.keywords,
        active=model.active,
        discovery_mode=model.discovery_mode,
    )


def _to_opportunity(model: OpportunityModel) -> Opportunity:
    opp = Opportunity(
        id=OpportunityId(UUID(model.id)),
        topic=model.topic,
        score=OpportunityScore(
            trend_velocity=model.trend_velocity,
            competition_gap=model.competition_gap,
            social_signal=model.social_signal,
            monetization_intent=model.monetization_intent,
            frustration_level=model.frustration_level,
            total=model.total,
            confidence=model.confidence,
        ),
        recommended_action=model.recommended_action,
        domain_applicability=model.domain_applicability,
        domain_reasoning=model.domain_reasoning,
        evidence=_deserialize_evidence(model.evidence_json),
    )
    return opp


def _to_briefing(model: BriefingModel) -> Briefing:
    return Briefing(
        id=BriefingId(UUID(model.id)),
        niche_id=NicheId(UUID(model.niche_id)),
        opportunities=[_to_opportunity(o) for o in model.opportunities],
        generated_at=model.generated_at,
    )


class SqlApiKeyRepository(ApiKeyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_hash(self, key_hash: str) -> ApiKey | None:
        result = await self._session.execute(
            select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash)
        )
        row = result.scalar_one_or_none()
        return _to_api_key(row) if row else None

    async def save(self, api_key: ApiKey) -> None:
        model = ApiKeyModel(
            id=api_key.id,
            client_name=api_key.client_name,
            key_hash=api_key.key_hash,
            scopes_json=json.dumps(api_key.scopes),
            active=api_key.active,
            created_at=api_key.created_at,
            expires_at=api_key.expires_at,
            tier=api_key.tier,
            monthly_quota_used=api_key.monthly_quota_used,
            quota_reset_at=api_key.quota_reset_at,
        )
        self._session.add(model)
        await self._session.commit()

    async def revoke(self, key_id: str) -> None:
        result = await self._session.execute(
            select(ApiKeyModel).where(ApiKeyModel.id == key_id)
        )
        row = result.scalar_one_or_none()
        if row:
            row.active = False
            await self._session.commit()

    async def list_all(self) -> list[ApiKey]:
        result = await self._session.execute(select(ApiKeyModel))
        return [_to_api_key(r) for r in result.scalars().all()]


def _to_api_key(model: ApiKeyModel) -> ApiKey:
    return ApiKey(
        id=model.id,
        client_name=model.client_name,
        key_hash=model.key_hash,
        scopes=json.loads(model.scopes_json),
        active=model.active,
        created_at=model.created_at,
        expires_at=model.expires_at,
        tier=model.tier,
        monthly_quota_used=model.monthly_quota_used,
        quota_reset_at=model.quota_reset_at,
    )


class SqlAlertRuleRepository(AlertRuleRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, rule: AlertRule) -> None:
        model = _alert_rule_to_model(rule)
        await self._session.merge(model)
        await self._session.flush()

    async def find_by_id(self, rule_id: AlertRuleId) -> AlertRule | None:
        result = await self._session.get(AlertRuleModel, str(rule_id))
        return _alert_rule_to_entity(result) if result else None

    async def find_active_by_niche(self, niche_id: str) -> list[AlertRule]:
        stmt = select(AlertRuleModel).where(
            AlertRuleModel.niche_id == niche_id,
            AlertRuleModel.active.is_(True),
        )
        result = await self._session.execute(stmt)
        return [_alert_rule_to_entity(m) for m in result.scalars().all()]

    async def deactivate(self, rule_id: AlertRuleId) -> None:
        stmt = (
            update(AlertRuleModel)
            .where(AlertRuleModel.id == str(rule_id))
            .values(active=False)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def list_all(self, niche_id: str | None = None) -> list[AlertRule]:
        stmt = select(AlertRuleModel)
        if niche_id:
            stmt = stmt.where(AlertRuleModel.niche_id == niche_id)
        result = await self._session.execute(stmt)
        return [_alert_rule_to_entity(m) for m in result.scalars().all()]


def _alert_rule_to_model(rule: AlertRule) -> AlertRuleModel:
    return AlertRuleModel(
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


def _alert_rule_to_entity(model: AlertRuleModel) -> AlertRule:
    return AlertRule(
        id=AlertRuleId(UUID(model.id)),
        niche_id=model.niche_id,
        threshold_score=model.threshold_score,
        delivery_channel=model.delivery_channel,
        webhook_url=model.webhook_url,
        email=model.email,
        active=model.active,
        last_notified_at=model.last_notified_at,
        created_at=model.created_at,
    )

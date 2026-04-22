from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from domain.entities.briefing import Briefing
from domain.entities.niche import Niche, NicheId
from domain.entities.opportunity import Opportunity
from domain.value_objects.opportunity_score import OpportunityScore
from infrastructure.db.models import Base
from infrastructure.db.repositories import SQLBriefingRepository, SQLNicheRepository
from infrastructure.db.session import get_session
from main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def session():
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


@pytest.fixture
def client(session: AsyncSession):
    async def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


def _make_score(total: float = 75.0) -> OpportunityScore:
    return OpportunityScore(
        trend_velocity=7.0,
        competition_gap=7.0,
        social_signal=7.0,
        monetization_intent=8.0,
        total=total,
        confidence="high",
    )


async def test_get_briefing_when_exists_then_200(client: TestClient, session: AsyncSession) -> None:
    niche = Niche.create("Angular", ["angular signals"])
    await SQLNicheRepository(session).save(niche)

    opp = Opportunity.create(topic="angular signals", score=_make_score())
    opp.recommended_action = "Crear tutorial esta semana"
    briefing = Briefing.create(niche_id=niche.id, opportunities=[opp])
    await SQLBriefingRepository(session).save(briefing)

    resp = client.get(f"/briefing/{niche.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["niche_id"] == str(niche.id)
    assert len(data["opportunities"]) == 1
    assert data["opportunities"][0]["recommended_action"] == "Crear tutorial esta semana"


async def test_get_briefing_when_not_found_then_404(client: TestClient) -> None:
    resp = client.get(f"/briefing/{uuid4()}")
    assert resp.status_code == 404

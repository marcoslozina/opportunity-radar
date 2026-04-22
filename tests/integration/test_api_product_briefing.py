from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from domain.entities.niche import Niche
from domain.entities.product_briefing import ProductBriefing
from domain.entities.product_opportunity import ProductOpportunity
from domain.value_objects.profitability_score import ProfitabilityScore
from infrastructure.db.models import Base
from infrastructure.db.product_repositories import SQLProductBriefingRepository
from infrastructure.db.repositories import SQLNicheRepository
from infrastructure.db.session import get_session
from main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

_NOW = datetime.now(tz=timezone.utc)


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
def client(session: AsyncSession, monkeypatch):
    async def override_session():
        yield session

    monkeypatch.setattr("infrastructure.scheduler.pipeline_scheduler.add_niche_job", lambda *a: None)
    monkeypatch.setattr("infrastructure.scheduler.pipeline_scheduler.remove_niche_job", lambda *a: None)

    app.dependency_overrides[get_session] = override_session
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


def _make_score(total: float = 60.0) -> ProfitabilityScore:
    return ProfitabilityScore(
        frustration_level=6.0,
        market_size=6.0,
        competition_gap=6.0,
        willingness_to_pay=6.0,
        total=total,
        confidence="high",
    )


def _make_opportunity(niche_id: str, topic: str, total: float = 60.0) -> ProductOpportunity:
    return ProductOpportunity(
        id=str(uuid4()),
        niche_id=niche_id,
        topic=topic,
        score=_make_score(total),
        product_type=None,
        product_reasoning="",
        recommended_price_range="",
        created_at=_NOW,
    )


async def test_get_product_briefing_200(client: TestClient, session: AsyncSession) -> None:
    niche = Niche.create("Python", ["python async"])
    await SQLNicheRepository(session).save(niche)

    opportunities = [
        _make_opportunity(str(niche.id), f"topic-{i}", float(i * 10))
        for i in range(1, 6)
    ]
    briefing = ProductBriefing(
        id=str(uuid4()),
        niche_id=str(niche.id),
        opportunities=opportunities,
        generated_at=_NOW,
    )
    await SQLProductBriefingRepository(session).save(briefing)

    resp = client.get(f"/product-briefing/{niche.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["niche_id"] == str(niche.id)
    assert len(data["opportunities"]) == 5


async def test_get_product_briefing_404(client: TestClient) -> None:
    resp = client.get(f"/product-briefing/{uuid4()}")
    assert resp.status_code == 404

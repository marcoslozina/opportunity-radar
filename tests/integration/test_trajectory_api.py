from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.dependencies.api_key import get_api_key
from domain.entities.briefing import Briefing
from domain.entities.niche import Niche, NicheId
from domain.entities.opportunity import Opportunity
from domain.value_objects.api_key_context import ApiKeyContext
from domain.value_objects.opportunity_score import OpportunityScore
from infrastructure.db.models import Base
from infrastructure.db.repositories import SQLBriefingRepository, SQLNicheRepository
from infrastructure.db.session import get_session
from main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

_FAKE_API_KEY_CTX = ApiKeyContext(
    client_name="test-client",
    scopes=("read",),
    key_id="00000000-0000-0000-0000-000000000001",
)

_NOW = datetime(2026, 5, 5, 8, 0, 0)
_YESTERDAY = _NOW - timedelta(days=7)


def _make_score(total: float) -> OpportunityScore:
    return OpportunityScore(
        trend_velocity=7.0,
        competition_gap=7.0,
        social_signal=7.0,
        monetization_intent=8.0,
        frustration_level=0.0,
        total=total,
        confidence="high",
    )


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

    async def override_api_key() -> ApiKeyContext:
        return _FAKE_API_KEY_CTX

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_api_key] = override_api_key
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


async def test_trajectory_when_two_briefings_then_matched_topic_has_trajectory(
    client: TestClient,
    session: AsyncSession,
) -> None:
    niche = Niche.create("Real Estate Argentina", ["departamentos"])
    await SQLNicheRepository(session).save(niche)
    repo = SQLBriefingRepository(session)

    from domain.entities.briefing import BriefingId

    # Previous briefing (older)
    prev_opp = Opportunity.create(topic="Departamentos zona norte", score=_make_score(5.1))
    prev_briefing = Briefing(
        id=BriefingId(uuid4()),
        niche_id=niche.id,
        opportunities=[prev_opp],
        generated_at=_YESTERDAY,
    )
    await repo.save(prev_briefing)

    # Current briefing (newer) — same topic + one new topic
    curr_opp = Opportunity.create(topic="Departamentos zona norte", score=_make_score(7.2))
    new_opp = Opportunity.create(topic="Nueva oportunidad emergente", score=_make_score(6.0))
    curr_briefing = Briefing(
        id=BriefingId(uuid4()),
        niche_id=niche.id,
        opportunities=[curr_opp, new_opp],
        generated_at=_NOW,
    )
    await repo.save(curr_briefing)

    resp = client.get(f"/briefing/{niche.id}")

    assert resp.status_code == 200
    data = resp.json()
    opps = {o["topic"]: o for o in data["opportunities"]}

    # Matched topic should have trajectory
    matched = opps["Departamentos zona norte"]
    assert matched["trajectory"] is not None
    assert matched["trajectory"]["direction"] in ("GROWING ↑", "COOLING ↓", "STABLE →")
    assert matched["trajectory"]["direction"] == "GROWING ↑"
    assert matched["trajectory"]["delta"] == 2.1
    assert matched["trajectory"]["previous_total"] == 5.1

    # compared_at should match previous briefing's generated_at
    assert matched["trajectory"]["compared_at"].startswith(_YESTERDAY.isoformat())

    # New topic (not in previous) should have null trajectory
    new_topic = opps["Nueva oportunidad emergente"]
    assert new_topic["trajectory"] is None


async def test_trajectory_when_only_one_briefing_then_all_null(
    client: TestClient,
    session: AsyncSession,
) -> None:
    from domain.entities.briefing import BriefingId

    niche = Niche.create("Single Run Niche", ["keywords"])
    await SQLNicheRepository(session).save(niche)
    opp = Opportunity.create(topic="Solo topic", score=_make_score(7.0))
    briefing = Briefing(
        id=BriefingId(uuid4()),
        niche_id=niche.id,
        opportunities=[opp],
        generated_at=_NOW,
    )
    await SQLBriefingRepository(session).save(briefing)

    resp = client.get(f"/briefing/{niche.id}")

    assert resp.status_code == 200
    data = resp.json()
    for opportunity in data["opportunities"]:
        assert opportunity["trajectory"] is None

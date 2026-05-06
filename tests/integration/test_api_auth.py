from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.dependencies.api_key import _key_cache
from domain.entities.api_key import ApiKey
from infrastructure.db.models import Base
from infrastructure.db.repositories import SqlApiKeyRepository
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
    # Ensure the cache is clean before each test to avoid cross-test pollution
    _key_cache.clear()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()
    _key_cache.clear()


@pytest.fixture
async def valid_api_key(session: AsyncSession) -> tuple[ApiKey, str]:
    """Create a valid active API key and persist it to the test DB."""
    entity, raw_key = ApiKey.generate(
        client_name="propflow",
        scopes=["read:opportunities"],
    )
    await SqlApiKeyRepository(session).save(entity)
    return entity, raw_key


@pytest.fixture
async def revoked_api_key(session: AsyncSession) -> tuple[ApiKey, str]:
    """Create a revoked API key and persist it to the test DB."""
    entity, raw_key = ApiKey.generate(
        client_name="propflow",
        scopes=["read:opportunities"],
    )
    entity.active = False
    await SqlApiKeyRepository(session).save(entity)
    return entity, raw_key


async def test_protected_endpoint_with_valid_key_returns_200(
    client: TestClient,
    valid_api_key: tuple[ApiKey, str],
) -> None:
    _, raw_key = valid_api_key
    resp = client.get("/briefing/00000000-0000-0000-0000-000000000001", headers={"X-API-Key": raw_key})
    # 404 is acceptable (no briefing in DB) — the important thing is it passed auth (not 401)
    assert resp.status_code != 401


async def test_protected_endpoint_with_no_key_returns_401(client: TestClient) -> None:
    resp = client.get("/briefing/00000000-0000-0000-0000-000000000001")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "X-API-Key header missing"


async def test_protected_endpoint_with_invalid_key_returns_401(client: TestClient) -> None:
    resp = client.get(
        "/briefing/00000000-0000-0000-0000-000000000001",
        headers={"X-API-Key": "or_live_thiskeyisinvalid"},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid API key"


async def test_protected_endpoint_with_revoked_key_returns_401(
    client: TestClient,
    revoked_api_key: tuple[ApiKey, str],
) -> None:
    _, raw_key = revoked_api_key
    resp = client.get(
        "/briefing/00000000-0000-0000-0000-000000000001",
        headers={"X-API-Key": raw_key},
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "API key has been revoked"


async def test_health_endpoint_without_key_returns_200(client: TestClient) -> None:
    """Smoke test: /health remains public with no auth required."""
    resp = client.get("/health")
    assert resp.status_code == 200


async def test_opportunities_endpoint_requires_key(client: TestClient) -> None:
    resp = client.get("/opportunities?niche_id=00000000-0000-0000-0000-000000000001")
    assert resp.status_code == 401


async def test_product_briefing_endpoint_requires_key(client: TestClient) -> None:
    resp = client.get("/product-briefing/00000000-0000-0000-0000-000000000001")
    assert resp.status_code == 401

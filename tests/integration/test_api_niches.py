from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from infrastructure.db.models import Base
from infrastructure.db.session import get_session
from infrastructure.scheduler.pipeline_scheduler import add_niche_job, remove_niche_job
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
def client(session: AsyncSession, monkeypatch):
    async def override_session():
        yield session

    monkeypatch.setattr("infrastructure.scheduler.pipeline_scheduler.add_niche_job", lambda *a: None)
    monkeypatch.setattr("infrastructure.scheduler.pipeline_scheduler.remove_niche_job", lambda *a: None)

    app.dependency_overrides[get_session] = override_session
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


def test_create_niche_when_valid_then_201(client: TestClient) -> None:
    resp = client.post("/niches", json={"name": "Angular", "keywords": ["angular signals"]})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Angular"
    assert "id" in data


def test_create_niche_when_empty_keywords_then_422(client: TestClient) -> None:
    resp = client.post("/niches", json={"name": "Angular", "keywords": []})
    assert resp.status_code == 422


def test_delete_niche_when_exists_then_204(client: TestClient) -> None:
    create = client.post("/niches", json={"name": "React", "keywords": ["react hooks"]})
    niche_id = create.json()["id"]

    resp = client.delete(f"/niches/{niche_id}")
    assert resp.status_code == 204


def test_delete_niche_when_not_found_then_404(client: TestClient) -> None:
    from uuid import uuid4
    resp = client.delete(f"/niches/{uuid4()}")
    assert resp.status_code == 404


def test_create_niche_with_discovery_mode_product(client: TestClient) -> None:
    resp = client.post("/niches", json={"name": "Python", "keywords": ["python async"], "discovery_mode": "product"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["discovery_mode"] == "product"


def test_create_niche_invalid_discovery_mode(client: TestClient) -> None:
    resp = client.post("/niches", json={"name": "Python", "keywords": ["python async"], "discovery_mode": "unknown"})
    assert resp.status_code == 422

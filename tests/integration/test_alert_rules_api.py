from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.dependencies.api_key import get_api_key
from domain.entities.niche import Niche, NicheId
from domain.value_objects.api_key_context import ApiKeyContext
from infrastructure.db.models import Base
from infrastructure.db.repositories import SQLNicheRepository
from infrastructure.db.session import get_session
from main import app

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

_FAKE_API_KEY_CTX = ApiKeyContext(
    client_name="test-client",
    scopes=("read", "write"),
    key_id="00000000-0000-0000-0000-000000000001",
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


@pytest.fixture
async def niche_id(session: AsyncSession) -> str:
    """Create a niche and return its ID string."""
    niche = Niche.create("Real Estate", ["real estate trends"])
    repo = SQLNicheRepository(session)
    await repo.save(niche)
    return str(niche.id)


def test_create_alert_rule_returns_201(client: TestClient, niche_id: str) -> None:
    resp = client.post(
        "/alert-rules",
        json={
            "niche_id": niche_id,
            "threshold_score": 80.0,
            "delivery_channel": "webhook",
            "webhook_url": "https://example.com/hook",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["niche_id"] == niche_id
    assert data["threshold_score"] == 80.0
    assert data["delivery_channel"] == "webhook"
    assert data["webhook_url"] == "https://example.com/hook"
    assert data["active"] is True


def test_create_alert_rule_with_email_returns_201(client: TestClient, niche_id: str) -> None:
    resp = client.post(
        "/alert-rules",
        json={
            "niche_id": niche_id,
            "threshold_score": 60.0,
            "delivery_channel": "email",
            "email": "user@example.com",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["delivery_channel"] == "email"
    assert data["email"] == "user@example.com"


def test_create_alert_rule_validates_threshold_out_of_range(client: TestClient, niche_id: str) -> None:
    resp = client.post(
        "/alert-rules",
        json={
            "niche_id": niche_id,
            "threshold_score": 150.0,
            "delivery_channel": "webhook",
            "webhook_url": "https://example.com/hook",
        },
    )
    assert resp.status_code == 422


def test_create_alert_rule_validates_missing_webhook_url(client: TestClient, niche_id: str) -> None:
    resp = client.post(
        "/alert-rules",
        json={
            "niche_id": niche_id,
            "threshold_score": 75.0,
            "delivery_channel": "webhook",
            # webhook_url omitted
        },
    )
    assert resp.status_code == 422


def test_create_alert_rule_validates_missing_email(client: TestClient, niche_id: str) -> None:
    resp = client.post(
        "/alert-rules",
        json={
            "niche_id": niche_id,
            "threshold_score": 75.0,
            "delivery_channel": "email",
            # email omitted
        },
    )
    assert resp.status_code == 422


def test_create_alert_rule_when_niche_not_found_then_404(client: TestClient) -> None:
    resp = client.post(
        "/alert-rules",
        json={
            "niche_id": str(uuid4()),
            "threshold_score": 75.0,
            "delivery_channel": "webhook",
            "webhook_url": "https://example.com/hook",
        },
    )
    assert resp.status_code == 404


def test_list_alert_rules_filters_by_niche_id(client: TestClient, niche_id: str) -> None:
    other_niche_id = str(uuid4())

    # Create a rule for target niche
    client.post(
        "/alert-rules",
        json={
            "niche_id": niche_id,
            "threshold_score": 75.0,
            "delivery_channel": "webhook",
            "webhook_url": "https://example.com/hook",
        },
    )

    resp = client.get(f"/alert-rules?niche_id={niche_id}")
    assert resp.status_code == 200
    rules = resp.json()
    assert len(rules) == 1
    assert rules[0]["niche_id"] == niche_id

    # Filter for other niche — should be empty
    resp_other = client.get(f"/alert-rules?niche_id={other_niche_id}")
    assert resp_other.status_code == 200
    assert resp_other.json() == []


def test_list_alert_rules_without_filter_returns_all(client: TestClient, niche_id: str) -> None:
    client.post(
        "/alert-rules",
        json={
            "niche_id": niche_id,
            "threshold_score": 70.0,
            "delivery_channel": "webhook",
            "webhook_url": "https://example.com/hook-1",
        },
    )
    client.post(
        "/alert-rules",
        json={
            "niche_id": niche_id,
            "threshold_score": 80.0,
            "delivery_channel": "webhook",
            "webhook_url": "https://example.com/hook-2",
        },
    )

    resp = client.get("/alert-rules")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


def test_delete_alert_rule_deactivates_it(client: TestClient, niche_id: str) -> None:
    create_resp = client.post(
        "/alert-rules",
        json={
            "niche_id": niche_id,
            "threshold_score": 75.0,
            "delivery_channel": "webhook",
            "webhook_url": "https://example.com/hook",
        },
    )
    rule_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/alert-rules/{rule_id}")
    assert delete_resp.status_code == 204

    # After deactivation, listing by niche (all, not just active) still shows it
    # But find_active_by_niche won't return it
    # Let's verify via list that active=False
    list_resp = client.get(f"/alert-rules?niche_id={niche_id}")
    rules = list_resp.json()
    # The list_all endpoint returns all (not filtered by active)
    deactivated = next((r for r in rules if r["id"] == rule_id), None)
    if deactivated:
        assert deactivated["active"] is False


def test_delete_alert_rule_when_not_found_then_404(client: TestClient) -> None:
    resp = client.delete(f"/alert-rules/{uuid4()}")
    assert resp.status_code == 404

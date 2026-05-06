from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from api.dependencies.api_key import _key_cache, get_api_key
from domain.entities.api_key import ApiKey
from domain.value_objects.api_key_context import ApiKeyContext
from infrastructure.db.session import get_session


def _key_with_tier(tier: str) -> ApiKey:
    entity, _ = ApiKey.generate(client_name="test-client", scopes=["read"])
    entity.tier = tier
    return entity


def _make_app(api_key_entity: ApiKey) -> tuple[FastAPI, AsyncMock]:
    app = FastAPI()
    mock_repo = AsyncMock()
    mock_repo.find_by_hash.return_value = api_key_entity

    async def fake_session():
        yield MagicMock()

    app.dependency_overrides[get_session] = fake_session

    @app.get("/protected")
    async def route(ctx: ApiKeyContext = Depends(get_api_key)) -> dict[str, str]:
        return {"tier": ctx.tier}

    return app, mock_repo


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    _key_cache.clear()


class TestQuotaUnderLimit:
    def test_returns_200_when_under_quota(self) -> None:
        """Requests below the monthly limit pass through normally."""
        entity = _key_with_tier("starter")  # limit: 100
        app, mock_repo = _make_app(entity)

        with patch("api.dependencies.api_key.SqlApiKeyRepository") as MockRepo, \
             patch("api.dependencies.api_key.increment_query_counter", new_callable=AsyncMock) as mock_counter:
            MockRepo.return_value = mock_repo
            mock_counter.return_value = 50  # 50 < 100

            with TestClient(app, raise_server_exceptions=False) as c:
                resp = c.get("/protected", headers={"X-API-Key": "or_live_testtoken"})

        assert resp.status_code == 200
        assert resp.json()["tier"] == "starter"
        mock_counter.assert_awaited_once_with(entity.id)


class TestQuotaExceeded:
    def test_returns_429_when_quota_exceeded(self) -> None:
        """Requests over the monthly limit receive 429 with upgrade message."""
        entity = _key_with_tier("starter")  # limit: 100
        app, mock_repo = _make_app(entity)

        with patch("api.dependencies.api_key.SqlApiKeyRepository") as MockRepo, \
             patch("api.dependencies.api_key.increment_query_counter", new_callable=AsyncMock) as mock_counter:
            MockRepo.return_value = mock_repo
            mock_counter.return_value = 101  # 101 > 100

            with TestClient(app, raise_server_exceptions=False) as c:
                resp = c.get("/protected", headers={"X-API-Key": "or_live_testtoken"})

        assert resp.status_code == 429
        assert "100" in resp.json()["detail"]
        assert "Upgrade" in resp.json()["detail"]

    def test_returns_429_at_exact_limit_plus_one(self) -> None:
        """Boundary: limit + 1 is rejected."""
        entity = _key_with_tier("professional")  # limit: 1000
        app, mock_repo = _make_app(entity)

        with patch("api.dependencies.api_key.SqlApiKeyRepository") as MockRepo, \
             patch("api.dependencies.api_key.increment_query_counter", new_callable=AsyncMock) as mock_counter:
            MockRepo.return_value = mock_repo
            mock_counter.return_value = 1001

            with TestClient(app, raise_server_exceptions=False) as c:
                resp = c.get("/protected", headers={"X-API-Key": "or_live_protoken"})

        assert resp.status_code == 429


class TestQuotaRedisDown:
    def test_returns_200_when_redis_unavailable(self) -> None:
        """Quota check fails open: Redis down never blocks a request."""
        entity = _key_with_tier("starter")
        app, mock_repo = _make_app(entity)

        with patch("api.dependencies.api_key.SqlApiKeyRepository") as MockRepo, \
             patch("api.dependencies.api_key.increment_query_counter", new_callable=AsyncMock) as mock_counter:
            MockRepo.return_value = mock_repo
            mock_counter.return_value = -1  # Redis unavailable sentinel

            with TestClient(app, raise_server_exceptions=False) as c:
                resp = c.get("/protected", headers={"X-API-Key": "or_live_testtoken"})

        assert resp.status_code == 200

    def test_counter_still_called_when_redis_down(self) -> None:
        """The counter is attempted even when Redis is down — it's the counter that returns -1."""
        entity = _key_with_tier("starter")
        app, mock_repo = _make_app(entity)

        with patch("api.dependencies.api_key.SqlApiKeyRepository") as MockRepo, \
             patch("api.dependencies.api_key.increment_query_counter", new_callable=AsyncMock) as mock_counter:
            MockRepo.return_value = mock_repo
            mock_counter.return_value = -1

            with TestClient(app, raise_server_exceptions=False) as c:
                c.get("/protected", headers={"X-API-Key": "or_live_testtoken"})

        mock_counter.assert_awaited_once()


class TestQuotaEnterprise:
    def test_counter_never_called_for_unlimited_tier(self) -> None:
        """Enterprise tier (max=-1) skips the counter entirely."""
        entity = _key_with_tier("enterprise")
        app, mock_repo = _make_app(entity)

        with patch("api.dependencies.api_key.SqlApiKeyRepository") as MockRepo, \
             patch("api.dependencies.api_key.increment_query_counter", new_callable=AsyncMock) as mock_counter:
            MockRepo.return_value = mock_repo

            with TestClient(app, raise_server_exceptions=False) as c:
                resp = c.get("/protected", headers={"X-API-Key": "or_live_enterprise"})

        assert resp.status_code == 200
        mock_counter.assert_not_awaited()

    def test_enterprise_always_200_regardless_of_usage(self) -> None:
        """Enterprise is unlimited — even if counter were called with a huge number, no 429."""
        entity = _key_with_tier("enterprise")
        app, mock_repo = _make_app(entity)

        with patch("api.dependencies.api_key.SqlApiKeyRepository") as MockRepo, \
             patch("api.dependencies.api_key.increment_query_counter", new_callable=AsyncMock) as mock_counter:
            MockRepo.return_value = mock_repo
            mock_counter.return_value = 999_999

            with TestClient(app, raise_server_exceptions=False) as c:
                resp = c.get("/protected", headers={"X-API-Key": "or_live_enterprise"})

        assert resp.status_code == 200

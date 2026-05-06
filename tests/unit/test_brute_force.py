from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from api.dependencies.api_key import _key_cache, get_api_key
from domain.entities.api_key import ApiKey
from domain.value_objects.api_key_context import ApiKeyContext
from infrastructure.db.session import get_session


def _make_app_invalid_key() -> FastAPI:
    """App where the DB always returns None (invalid key)."""
    app = FastAPI()
    mock_repo = AsyncMock()
    mock_repo.find_by_hash.return_value = None

    async def fake_session():
        yield MagicMock()

    app.dependency_overrides[get_session] = fake_session

    @app.get("/protected")
    async def route(ctx: ApiKeyContext = Depends(get_api_key)) -> dict[str, str]:
        return {"ok": "true"}

    return app


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    _key_cache.clear()


class TestBruteForceInvalidKey:
    def test_429_after_16_failed_attempts_with_invalid_key(self) -> None:
        """16 consecutive attempts with an invalid key triggers 429 lockout."""
        app = _make_app_invalid_key()

        call_count = 0

        async def fake_incr(key: str) -> int:
            nonlocal call_count
            call_count += 1
            return call_count

        mock_redis = MagicMock()
        mock_redis.incr = fake_incr
        mock_redis.expire = AsyncMock()

        async def fake_get_redis():
            return mock_redis

        with (
            patch("api.dependencies.api_key.SqlApiKeyRepository") as MockRepo,
            patch("api.middleware.auth_guard.get_redis", new=fake_get_redis),
        ):
            MockRepo.return_value.find_by_hash = AsyncMock(return_value=None)
            with TestClient(app, raise_server_exceptions=False) as c:
                responses = [
                    c.get("/protected", headers={"X-API-Key": "or_live_badkey"})
                    for _ in range(16)
                ]

        # First 15 should be 401 (invalid key), 16th should be 429 (locked out)
        for resp in responses[:15]:
            assert resp.status_code == 401
        assert responses[15].status_code == 429
        assert "Too many failed attempts" in responses[15].json()["detail"]

    def test_redis_unavailable_does_not_block(self) -> None:
        """When Redis is unavailable, brute force check fails open — request gets 401, never 429."""
        app = _make_app_invalid_key()

        async def fake_get_redis_none():
            return None

        with (
            patch("api.dependencies.api_key.SqlApiKeyRepository") as MockRepo,
            patch("api.middleware.auth_guard.get_redis", new=fake_get_redis_none),
        ):
            MockRepo.return_value.find_by_hash = AsyncMock(return_value=None)
            with TestClient(app, raise_server_exceptions=False) as c:
                responses = [
                    c.get("/protected", headers={"X-API-Key": "or_live_badkey"})
                    for _ in range(20)
                ]

        for resp in responses:
            assert resp.status_code == 401

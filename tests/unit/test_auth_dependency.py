from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from cachetools import TTLCache
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from api.dependencies.api_key import _make_get_api_key
from domain.entities.api_key import ApiKey
from domain.value_objects.api_key_context import ApiKeyContext
from infrastructure.db.session import get_session


def _active_key(expires_at: datetime | None = None, active: bool = True) -> ApiKey:
    entity, _ = ApiKey.generate(client_name="propflow", scopes=["read:opportunities"])
    entity.active = active
    entity.expires_at = expires_at
    return entity


def _make_test_app(find_by_hash_return: ApiKey | None = None) -> tuple[FastAPI, AsyncMock]:
    """Build a minimal FastAPI test app with the get_api_key dependency wired.

    Each call creates a fresh TTLCache so tests are fully isolated without
    relying on _key_cache.clear() between runs.
    """
    fresh_cache: TTLCache = TTLCache(maxsize=512, ttl=300)
    get_api_key = _make_get_api_key(cache=fresh_cache)

    test_app = FastAPI()
    mock_instance = AsyncMock()
    mock_instance.find_by_hash.return_value = find_by_hash_return

    async def fake_session():
        yield MagicMock()

    test_app.dependency_overrides[get_session] = fake_session

    @test_app.get("/protected")
    async def route(ctx: ApiKeyContext = Depends(get_api_key)) -> dict[str, str]:
        return {"client": ctx.client_name}

    return test_app, mock_instance


def test_get_api_key_when_header_missing_then_401() -> None:
    test_app, _ = _make_test_app()
    with TestClient(test_app, raise_server_exceptions=False) as c:
        resp = c.get("/protected")
    assert resp.status_code == 401
    assert resp.json()["detail"] == "X-API-Key header missing or invalid JWT"


def test_get_api_key_when_key_not_found_then_401() -> None:
    test_app, mock_instance = _make_test_app(find_by_hash_return=None)
    with patch("api.dependencies.api_key.SqlApiKeyRepository") as MockRepo:
        MockRepo.return_value = mock_instance
        with TestClient(test_app, raise_server_exceptions=False) as c:
            resp = c.get("/protected", headers={"X-API-Key": "or_live_doesnotexist"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid API key"


def test_get_api_key_when_key_revoked_then_401() -> None:
    revoked_key = _active_key(active=False)
    test_app, mock_instance = _make_test_app(find_by_hash_return=revoked_key)
    with patch("api.dependencies.api_key.SqlApiKeyRepository") as MockRepo:
        MockRepo.return_value = mock_instance
        with TestClient(test_app, raise_server_exceptions=False) as c:
            resp = c.get("/protected", headers={"X-API-Key": "or_live_revokedtoken"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "API key has been revoked"


def test_get_api_key_when_key_expired_then_401() -> None:
    expired_key = _active_key(expires_at=datetime.utcnow() - timedelta(hours=1))
    test_app, mock_instance = _make_test_app(find_by_hash_return=expired_key)
    with patch("api.dependencies.api_key.SqlApiKeyRepository") as MockRepo:
        MockRepo.return_value = mock_instance
        with TestClient(test_app, raise_server_exceptions=False) as c:
            resp = c.get("/protected", headers={"X-API-Key": "or_live_expiredtoken"})
    assert resp.status_code == 401
    assert resp.json()["detail"] == "API key has expired"


def test_get_api_key_when_valid_key_then_returns_context() -> None:
    valid_key = _active_key()
    test_app, mock_instance = _make_test_app(find_by_hash_return=valid_key)
    with patch("api.dependencies.api_key.SqlApiKeyRepository") as MockRepo:
        MockRepo.return_value = mock_instance
        with TestClient(test_app, raise_server_exceptions=False) as c:
            resp = c.get("/protected", headers={"X-API-Key": "or_live_validtoken"})
    assert resp.status_code == 200
    assert resp.json()["client"] == "propflow"


def test_get_api_key_cache_hit_skips_db() -> None:
    valid_key = _active_key()
    test_app, mock_instance = _make_test_app(find_by_hash_return=valid_key)
    raw_key = "or_live_cachetest_unique_12345"
    with patch("api.dependencies.api_key.SqlApiKeyRepository") as MockRepo:
        MockRepo.return_value = mock_instance
        with TestClient(test_app, raise_server_exceptions=False) as c:
            # First request — cache miss, DB is called
            c.get("/protected", headers={"X-API-Key": raw_key})
            # Second request — cache hit, DB should NOT be called again
            c.get("/protected", headers={"X-API-Key": raw_key})

    # find_by_hash should have been called exactly once (first request only)
    assert mock_instance.find_by_hash.call_count == 1

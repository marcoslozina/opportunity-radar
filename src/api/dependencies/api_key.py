from __future__ import annotations

from datetime import datetime

from cachetools import TTLCache
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.api_key import ApiKey
from domain.value_objects.api_key_context import ApiKeyContext
from infrastructure.db.repositories import SqlApiKeyRepository
from infrastructure.db.session import get_session

# Module-level TTL cache: maxsize=512, ttl=300s (5 minutes).
# NOTE: TTLCache is NOT thread-safe. Safe under asyncio (single-threaded event loop).
# If uvicorn is run with multiple sync workers, wrap access in threading.Lock.
_key_cache: TTLCache[str, ApiKeyContext] = TTLCache(maxsize=512, ttl=300)


async def get_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    session: AsyncSession = Depends(get_session),
) -> ApiKeyContext:
    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header missing",
        )

    key_hash = ApiKey.hash_raw(x_api_key)

    cached = _key_cache.get(key_hash)
    if cached is not None:
        request.state.api_key_ctx = cached
        return cached

    repo = SqlApiKeyRepository(session)
    api_key = await repo.find_by_hash(key_hash)

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    if not api_key.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has been revoked",
        )
    if api_key.expires_at is not None and api_key.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
        )

    ctx = ApiKeyContext(
        client_name=api_key.client_name,
        scopes=tuple(api_key.scopes),
        key_id=api_key.id,
    )
    _key_cache[key_hash] = ctx
    request.state.api_key_ctx = ctx
    return ctx

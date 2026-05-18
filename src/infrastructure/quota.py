from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

_redis_pool: object | None = None


async def get_redis() -> object | None:
    """Return a shared Redis connection pool instance.

    Uses a module-level singleton so connections are reused instead of
    creating (and leaking) a new connection on every call.
    """
    global _redis_pool
    if _redis_pool is not None:
        return _redis_pool
    try:
        import redis.asyncio as aioredis  # type: ignore[import]
        _redis_pool = await aioredis.from_url(REDIS_URL, decode_responses=True)
        return _redis_pool
    except Exception:
        return None


async def increment_query_counter(api_key_id: str) -> int:
    """Increment monthly query counter for the given api_key_id.

    Returns the new counter value, or -1 if Redis is unavailable.
    INCR + EXPIRE are executed atomically via pipeline to avoid race conditions.
    """
    month = datetime.now(UTC).strftime("%Y-%m")
    key = f"quota:{api_key_id}:{month}"
    r = await get_redis()
    if r is None:
        return -1
    try:
        # Pipeline atómico: INCR + EXPIRE en una sola operación
        async with r.pipeline(transaction=True) as pipe:
            await pipe.incr(key)
            await pipe.expire(key, 60 * 60 * 24 * 35)
            results = await pipe.execute()
        return int(results[0])
    except Exception as e:
        logging.error(f"[QUOTA] Redis error for {api_key_id[:8]}: {e}")
        return -1


async def get_query_count(api_key_id: str) -> int:
    """Return current monthly query count for the given api_key_id.

    Returns 0 if Redis is unavailable or the key does not exist.
    """
    month = datetime.now(UTC).strftime("%Y-%m")
    key = f"quota:{api_key_id}:{month}"
    r = await get_redis()
    if r is None:
        return 0
    try:
        val = await r.get(key)
        return int(val) if val else 0
    except Exception as e:
        logging.error(
            f"[QUOTA] get_query_count failed for {api_key_id[:8]}: {type(e).__name__}: {e}"
        )
        return 0

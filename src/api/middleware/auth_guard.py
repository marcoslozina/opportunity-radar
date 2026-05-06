from __future__ import annotations

import logging

from fastapi import HTTPException, Request, status

from core.circuit_breaker import CircuitBreaker
from infrastructure.quota import get_redis

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 600
LOCKOUT_THRESHOLD = 15
LOCKOUT_SECONDS = 900

_redis_cb = CircuitBreaker()


async def check_brute_force(request: Request) -> None:
    if _redis_cb.is_open():
        logger.warning("circuit_breaker_open component=brute_force — skipping Redis call")
        return
    r = await get_redis()
    if r is None:
        return
    ip = request.client.host if request.client else "unknown"
    key = f"failed_auth:{ip}"
    try:
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, WINDOW_SECONDS)
        if count > LOCKOUT_THRESHOLD:
            logger.warning(f"brute_force_lockout ip={ip} count={count}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed attempts. Try again later.",
            )
        _redis_cb.record_success()
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"brute_force_check_failed error={e}")
        _redis_cb.record_failure()


async def reset_brute_force(request: Request) -> None:
    if _redis_cb.is_open():
        logger.warning("circuit_breaker_open component=reset_brute_force — skipping Redis call")
        return
    r = await get_redis()
    if r is None:
        return
    ip = request.client.host if request.client else "unknown"
    try:
        await r.delete(f"failed_auth:{ip}")
        _redis_cb.record_success()
    except Exception as e:
        logger.warning(f"reset_brute_force_failed error={e}")
        _redis_cb.record_failure()

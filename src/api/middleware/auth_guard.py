from __future__ import annotations
import logging
from fastapi import HTTPException, Request, status
from infrastructure.quota import get_redis

logger = logging.getLogger(__name__)

WINDOW_SECONDS = 600
LOCKOUT_THRESHOLD = 15
LOCKOUT_SECONDS = 900


async def check_brute_force(request: Request) -> None:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"brute_force_check_failed error={e}")


async def reset_brute_force(request: Request) -> None:
    r = await get_redis()
    if r is None:
        return
    ip = request.client.host if request.client else "unknown"
    try:
        await r.delete(f"failed_auth:{ip}")
    except Exception:
        pass

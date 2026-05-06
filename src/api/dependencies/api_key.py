from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone

from cachetools import TTLCache
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.api_key import ApiKey
from domain.value_objects.api_key_context import ApiKeyContext
from domain.value_objects.tier import get_tier
from infrastructure.db.repositories import SqlApiKeyRepository
from infrastructure.db.session import get_session
from infrastructure.quota import increment_query_counter

# Module-level TTL cache: maxsize=512, ttl=300s (5 minutes).
# NOTE: TTLCache is NOT thread-safe. Safe under asyncio (single-threaded event loop).
# If uvicorn is run with multiple sync workers, wrap access in threading.Lock.
_key_cache: TTLCache[str, ApiKeyContext] = TTLCache(maxsize=512, ttl=300)


def _verify_supabase_jwt(token: str) -> dict | None:
    """Verifica un JWT de Supabase y retorna el payload si es válido."""
    secret = os.getenv("SUPABASE_JWT_SECRET", "")
    if not secret:
        return None
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts

        # Verificar firma
        msg = f"{header_b64}.{payload_b64}".encode()
        expected = base64.urlsafe_b64encode(
            hmac.new(secret.encode(), msg, hashlib.sha256).digest()
        ).rstrip(b"=").decode()

        if not hmac.compare_digest(expected, sig_b64):
            return None

        # Decodificar payload
        padding = 4 - len(payload_b64) % 4
        payload = json.loads(base64.urlsafe_b64decode(payload_b64 + "=" * padding))

        # Verificar expiración
        if payload.get("exp", 0) < time.time():
            return None

        return payload
    except Exception:
        return None


async def get_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    authorization: str | None = Header(default=None, alias="Authorization"),
    session: AsyncSession = Depends(get_session),
) -> ApiKeyContext:
    # Intentar JWT de Supabase primero
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
        payload = _verify_supabase_jwt(token)
        if payload:
            products = payload.get("user_metadata", {}).get("products", {})
            if "opportunity-radar" in products:
                tier = products["opportunity-radar"]
                ctx = ApiKeyContext(
                    client_name=payload.get("email", "supabase-user"),
                    scopes=("read", "write"),
                    key_id=payload.get("sub", ""),
                    tier=tier,
                )
                request.state.api_key_ctx = ctx
                return ctx

    if x_api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key header missing or invalid JWT",
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
    if api_key.expires_at is not None and api_key.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
        )

    ctx = ApiKeyContext(
        client_name=api_key.client_name,
        scopes=tuple(api_key.scopes),
        key_id=api_key.id,
        tier=api_key.tier,
    )
    _key_cache[key_hash] = ctx
    request.state.api_key_ctx = ctx

    # Enforce monthly quota (Redis-backed, fails open if Redis is unavailable)
    tier = get_tier(api_key.tier)
    if tier.max_opportunities_month != -1:
        count = await increment_query_counter(api_key.id)
        if count != -1 and count > tier.max_opportunities_month:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    f"Monthly quota exceeded ({tier.max_opportunities_month} requests). "
                    "Upgrade your plan."
                ),
            )

    return ctx

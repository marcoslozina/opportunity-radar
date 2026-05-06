from __future__ import annotations

from fastapi import Request
from slowapi import Limiter


def _get_client_ip(request: Request) -> str:
    """Return the real client IP, resolving Cloudflare and proxy headers.

    When Cloudflare is in front of the server, request.client.host returns
    the Cloudflare edge IP. Using it for rate limiting would create a shared
    bucket for ALL users instead of per-client isolation.

    Resolution order:
      1. CF-Connecting-IP  — Cloudflare passes the real client IP here
      2. X-Forwarded-For   — nginx or other proxies (leftmost entry)
      3. request.client.host — direct connection fallback
    """
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _key_func(request: Request) -> str:
    key = request.headers.get("X-API-Key", "").strip()
    return key if key else _get_client_ip(request)


limiter = Limiter(key_func=_key_func)

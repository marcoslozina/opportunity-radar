from __future__ import annotations

from fastapi import Request

from domain.value_objects.tier import get_tier


def get_rate_limit(request: Request) -> str:
    """Return dynamic rate limit string based on tier from request state."""
    ctx = getattr(request.state, "api_key_ctx", None)
    tier_name = getattr(ctx, "tier", "starter") if ctx else "starter"
    rpm = get_tier(tier_name).rate_limit_per_minute
    return f"{rpm}/minute"

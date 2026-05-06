"""Dual-write to shared Supabase portal after local provisioning.

Non-fatal: if Supabase write fails the subscription is still active
(local DB is source of truth for auth). The portal just won't show the key
until the next successful write.
"""
from __future__ import annotations

import hashlib
import logging
import os

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            return None
        from supabase import create_client
        _client = create_client(url, key)
    return _client


def _hash(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


async def provision_to_portal(
    user_id: str | None,
    email: str,
    raw_key: str,
    tier: str,
    _supabase_client=None,  # injectable para tests
) -> bool:
    """Write API key to the shared Supabase portal table.

    user_id comes from Supabase auth (may be None if user not yet invited).
    Falls back to invite_user_by_email if user_id is missing.
    """
    import asyncio

    def _sync() -> bool:
        supabase = _supabase_client or _get_client()
        if supabase is None:
            logger.warning("supabase_portal_not_configured — skipping dual-write")
            return False

        resolved_user_id = user_id

        if not resolved_user_id and email:
            try:
                res = supabase.auth.admin.invite_user_by_email(
                    email,
                    options={"data": {"tier": tier, "product": "opportunity-radar"}},
                )
                user = res.user if hasattr(res, "user") else None
                resolved_user_id = user.id if user else None
                logger.info("supabase_portal_user_invited", email=email)
            except Exception as e:
                logger.warning("supabase_portal_invite_failed", error=str(e))

        if not resolved_user_id:
            return False

        key_prefix = raw_key[:16]
        try:
            supabase.table("api_keys").upsert({
                "user_id": resolved_user_id,
                "key_hash": _hash(raw_key),
                "key_prefix": key_prefix,
                "tier": tier,
                "product": "opportunity-radar",
                "active": True,
            }, on_conflict="key_hash").execute()
            logger.info("supabase_portal_key_written", email=email, tier=tier)
            return True
        except Exception as e:
            logger.error("supabase_portal_write_failed", error=str(e))
            return False

    try:
        return await asyncio.to_thread(_sync)
    except Exception as e:
        logger.error("supabase_portal_provision_error", error=str(e))
        return False

"""Write billing events to the shared Supabase audit_log table.

Non-fatal: failures are logged but never propagate.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def log_billing_event(
    action: str,
    *,
    order_id: str | None = None,
    key_prefix: str | None = None,
    tier: str | None = None,
    email: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    import asyncio
    from infrastructure.supabase_provisioning import _get_client

    def _sync() -> None:
        supabase = _get_client()
        if supabase is None:
            return
        supabase.table("audit_log").insert({
            "product":    "opportunity-radar",
            "action":     action,
            "order_id":   order_id,
            "key_prefix": key_prefix,
            "tier":       tier,
            "email":      email,
            "metadata":   metadata or {},
        }).execute()

    try:
        await asyncio.to_thread(_sync)
        logger.info(f"audit_log_written action={action} product=opportunity-radar")
    except Exception as exc:
        logger.warning(f"audit_log_write_failed action={action} error={exc}")

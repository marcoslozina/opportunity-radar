from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.api_key import ApiKey
from infrastructure.audit_log import log_billing_event
from infrastructure.db.repositories import SqlApiKeyRepository
from infrastructure.supabase_provisioning import provision_to_portal


async def create_subscription(
    order_id: str,
    tier: str,
    email: str,
    session: AsyncSession,
) -> str:
    """Generate an API key and persist it after successful payment.

    Returns the raw (unhashed) API key shown once to the customer.
    Dual-writes to the shared Supabase portal (non-fatal if it fails).
    """
    api_key_entity, raw_key = ApiKey.generate(
        client_name=email,
        scopes=["read", "write"],
        expires_at=None,
    )
    api_key_entity.tier = tier

    repo = SqlApiKeyRepository(session)
    await repo.save(api_key_entity)

    await provision_to_portal(
        user_id=None,
        email=email,
        raw_key=raw_key,
        tier=tier,
    )

    await log_billing_event(
        "subscription_created",
        order_id=order_id,
        key_prefix=raw_key[:16],
        tier=tier,
        email=email,
    )

    return raw_key

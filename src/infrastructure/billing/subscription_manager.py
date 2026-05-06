from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.api_key import ApiKey
from infrastructure.db.repositories import SqlApiKeyRepository


async def create_subscription(
    order_id: str,
    tier: str,
    email: str,
    session: AsyncSession,
) -> str:
    """Generate an API key and persist it after successful payment.

    Returns the raw (unhashed) API key shown once to the customer.
    """
    api_key_entity, raw_key = ApiKey.generate(
        client_name=email,
        scopes=["read", "write"],
        expires_at=None,
    )
    api_key_entity.tier = tier

    repo = SqlApiKeyRepository(session)
    await repo.save(api_key_entity)
    # repo.save already commits — no second commit needed
    return raw_key

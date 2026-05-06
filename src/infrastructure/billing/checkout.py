from __future__ import annotations

import os

import httpx

LS_API_KEY = os.getenv("LS_API_KEY", "")
LS_STORE_ID = os.getenv("LS_STORE_ID", "")

VARIANT_IDS: dict[str, str] = {
    "starter": os.getenv("LS_VARIANT_STARTER", ""),
    "professional": os.getenv("LS_VARIANT_PROFESSIONAL", ""),
    "enterprise": os.getenv("LS_VARIANT_ENTERPRISE", ""),
}

LS_SUCCESS_URL = os.getenv(
    "LS_SUCCESS_URL", "https://opportunity-radar.marcoslozina.com/success"
)
LS_FAILURE_URL = os.getenv(
    "LS_FAILURE_URL", "https://opportunity-radar.marcoslozina.com/cancel"
)


async def create_checkout_session(tier: str, customer_email: str | None = None) -> str:
    variant_id = VARIANT_IDS.get(tier)
    if not variant_id:
        raise ValueError(f"No Lemon Squeezy variant configured for tier: {tier}")

    payload: dict = {
        "data": {
            "type": "checkouts",
            "attributes": {
                "checkout_data": {"email": customer_email} if customer_email else {},
                "product_options": {
                    "redirect_url": LS_SUCCESS_URL,
                },
            },
            "relationships": {
                "store": {"data": {"type": "stores", "id": LS_STORE_ID}},
                "variant": {"data": {"type": "variants", "id": variant_id}},
            },
        }
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.lemonsqueezy.com/v1/checkouts",
            json=payload,
            headers={
                "Authorization": f"Bearer {LS_API_KEY}",
                "Accept": "application/vnd.api+json",
                "Content-Type": "application/vnd.api+json",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["data"]["attributes"]["url"]  # type: ignore[no-any-return]

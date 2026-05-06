from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession

from .subscription_manager import create_subscription

LS_WEBHOOK_SECRET = os.getenv("LS_WEBHOOK_SECRET", "")

TIER_MAP: dict[str, str] = {
    "starter": "starter",
    "professional": "professional",
    "enterprise": "enterprise",
}

VARIANT_TO_TIER: dict[str, str] = {
    os.getenv("LS_VARIANT_STARTER", ""):      "starter",
    os.getenv("LS_VARIANT_PROFESSIONAL", ""): "professional",
    os.getenv("LS_VARIANT_ENTERPRISE", ""):   "enterprise",
}


def verify_signature(payload: bytes, signature: str) -> bool:
    if not LS_WEBHOOK_SECRET:
        if os.getenv("ENVIRONMENT", "development") == "production":
            logging.critical(
                "[BILLING] LS_WEBHOOK_SECRET not configured in production — rejecting webhook"
            )
            return False
        return True  # dev mode only
    expected = hmac.new(
        LS_WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def handle_webhook(
    payload: bytes,
    signature: str,
    session: AsyncSession,
) -> dict:
    if not verify_signature(payload, signature):
        raise ValueError("Invalid webhook signature")

    event = json.loads(payload)
    event_name = event.get("meta", {}).get("event_name", "")

    if event_name == "order_created":
        order_id = str(event["data"]["id"])
        email = event["data"]["attributes"].get("user_email", "")
        # Detect tier using exact variant ID match first, fall back to name
        first_order_item = event["data"]["attributes"].get("first_order_item", {})
        variant_id = str(first_order_item.get("variant_id", ""))
        tier = VARIANT_TO_TIER.get(variant_id)
        if not tier:
            variant_name = first_order_item.get("variant_name", "").lower()
            tier = next((t for t in TIER_MAP if variant_name == t), "starter")
            logging.warning(
                f"[BILLING] Variant ID {variant_id!r} not in VARIANT_TO_TIER map, "
                f"matched by name: {tier}"
            )
        raw_key = await create_subscription(order_id, tier, email, session)
        return {"status": "provisioned", "order_id": order_id, "tier": tier}

    return {"status": "ignored", "event": event_name}

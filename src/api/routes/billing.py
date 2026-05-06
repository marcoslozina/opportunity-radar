from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.api_key import get_api_key, ApiKeyContext
from domain.value_objects.tier import get_tier
from infrastructure.billing.checkout import create_checkout_session
from infrastructure.billing.webhook_handler import handle_webhook
from infrastructure.db.session import get_session
from infrastructure.quota import get_query_count

router = APIRouter(tags=["billing"])


class CheckoutRequest(BaseModel):
    tier: str
    email: str | None = None


class CheckoutResponse(BaseModel):
    checkout_url: str


@router.post("/billing/checkout", response_model=CheckoutResponse)
async def checkout(body: CheckoutRequest) -> CheckoutResponse:
    try:
        url = await create_checkout_session(body.tier, body.email)
        return CheckoutResponse(checkout_url=url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Checkout error: {e}")


@router.post("/billing/webhook", status_code=200)
async def webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    payload = await request.body()
    signature = request.headers.get("X-Signature", "")
    try:
        result = await handle_webhook(payload, signature, session)
        return result
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid signature")


@router.get("/billing/usage")
async def get_usage(ctx: ApiKeyContext = Depends(get_api_key)) -> dict:
    """Return current billing usage for the authenticated API key."""
    tier = get_tier(ctx.tier)
    queries_used = await get_query_count(ctx.key_id)

    now = datetime.now()
    if now.month == 12:
        reset = now.replace(day=1, month=1, year=now.year + 1, hour=0, minute=0, second=0, microsecond=0)
    else:
        reset = now.replace(day=1, month=now.month + 1, hour=0, minute=0, second=0, microsecond=0)

    unlimited = tier.max_opportunities_month == -1
    return {
        "tier": ctx.tier,
        "queries_used": queries_used,
        "queries_limit": None if unlimited else tier.max_opportunities_month,
        "queries_remaining": None if unlimited else max(0, tier.max_opportunities_month - queries_used),
        "reset_date": reset.strftime("%Y-%m-%d"),
        "features": {
            "briefings": tier.briefings,
            "product_discovery": tier.product_discovery,
            "export_csv": tier.export_csv,
        },
    }

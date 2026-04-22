from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ProfitabilityScoreResponse(BaseModel):
    frustration_level: float
    market_size: float
    competition_gap: float
    willingness_to_pay: float
    total: float
    confidence: str


class ProductOpportunityResponse(BaseModel):
    id: str
    topic: str
    score: ProfitabilityScoreResponse
    product_type: str | None
    product_reasoning: str
    recommended_price_range: str
    created_at: datetime


class ProductBriefingResponse(BaseModel):
    id: str
    niche_id: str
    generated_at: datetime
    opportunities: list[ProductOpportunityResponse]

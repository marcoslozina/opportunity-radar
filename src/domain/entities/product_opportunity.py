from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from domain.value_objects.product_type import ProductType
from domain.value_objects.profitability_score import ProfitabilityScore


@dataclass
class ProductOpportunity:
    id: str
    niche_id: str
    topic: str
    score: ProfitabilityScore
    product_type: ProductType | None
    product_reasoning: str
    recommended_price_range: str
    created_at: datetime

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from domain.entities.product_opportunity import ProductOpportunity


@dataclass
class ProductBriefing:
    id: str
    niche_id: str
    opportunities: list[ProductOpportunity]
    generated_at: datetime

    @property
    def top_5(self) -> list[ProductOpportunity]:
        sorted_opps = sorted(self.opportunities, key=lambda o: o.score.total, reverse=True)
        return sorted_opps[:5]

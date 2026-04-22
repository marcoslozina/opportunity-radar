from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from domain.entities.product_opportunity import ProductOpportunity
from domain.value_objects.product_type import ProductType


@dataclass(frozen=True)
class ProductClassification:
    product_type: ProductType
    reasoning: str
    recommended_price_range: str


class ProductDiscoveryPort(ABC):
    @abstractmethod
    async def classify(
        self, opportunities: list[ProductOpportunity]
    ) -> list[ProductClassification]: ...

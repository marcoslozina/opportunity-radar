from __future__ import annotations

from enum import Enum


class ProductType(str, Enum):
    EBOOK = "ebook"
    MICRO_SAAS = "micro-saas"
    SERVICE = "service"
    DIGITAL_PRODUCT = "digital-product"

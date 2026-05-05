from __future__ import annotations

from dataclasses import dataclass
from config import settings


@dataclass(frozen=True)
class NicheTemplate:
    name: str
    keywords: list[str]
    discovery_mode: str
    description: str


TEMPLATES: dict[str, NicheTemplate] = {
    "propflow": NicheTemplate(
        name="PropFlow Argentina",
        keywords=settings.propflow_keywords_ar,
        discovery_mode="real_estate",
        description="Oportunidades de contenido y producto en el mercado inmobiliario argentino con foco en créditos e inversión.",
    ),
    "esg_latam": NicheTemplate(
        name="ESG & Sustainability LATAM",
        keywords=settings.esg_keywords_latam,
        discovery_mode="esg_intelligence",
        description="Inteligencia de mercado sobre compliance ESG, señales regulatorias y gaps de herramientas en LATAM.",
    ),
}

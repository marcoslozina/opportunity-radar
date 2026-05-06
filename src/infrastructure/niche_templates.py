from __future__ import annotations

from dataclasses import dataclass

from infrastructure.niche_data import load_niche_keywords


@dataclass(frozen=True)
class NicheTemplate:
    name: str
    keywords: list[str]
    discovery_mode: str
    description: str


def _build_templates() -> dict[str, NicheTemplate]:
    kw = load_niche_keywords()
    return {
        "real_estate": NicheTemplate(
            name="Real Estate LATAM",
            keywords=kw.get("real_estate_ar", []),
            discovery_mode="real_estate",
            description="Oportunidades de contenido y producto en el mercado inmobiliario argentino con foco en créditos e inversión.",
        ),
        "esg_latam": NicheTemplate(
            name="ESG & Sustainability LATAM",
            keywords=kw.get("esg_latam", []),
            discovery_mode="esg_intelligence",
            description="Inteligencia de mercado sobre compliance ESG, señales regulatorias y gaps de herramientas en LATAM.",
        ),
    }


TEMPLATES: dict[str, NicheTemplate] = _build_templates()

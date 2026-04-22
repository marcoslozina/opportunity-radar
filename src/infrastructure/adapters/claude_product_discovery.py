from __future__ import annotations

import json
import logging

import anthropic

from config import Settings
from domain.entities.product_opportunity import ProductOpportunity
from domain.ports.product_discovery_port import ProductClassification, ProductDiscoveryPort
from domain.value_objects.product_type import ProductType

logger = logging.getLogger(__name__)

_FALLBACK_CLASSIFICATION = ProductClassification(
    product_type=ProductType.DIGITAL_PRODUCT,
    reasoning="Classification unavailable",
    recommended_price_range="$29–$99",
)

_SYSTEM_PROMPT = """Sos un experto en product strategy para indie makers y micro-empresas.
Tu tarea es clasificar oportunidades de producto según el tipo de producto más rentable para cada nicho.

Tipos válidos:
- "ebook": contenido educativo descargable
- "micro-saas": herramienta de software con suscripción
- "service": servicio prestado por humanos (freelance, agencia, consultoría)
- "digital-product": plantillas, assets, cursos, toolkits digitales

Respondé SOLO con un JSON array con esta estructura exacta:
[
  {
    "topic": "nombre del topic",
    "product_type": "uno de los tipos válidos",
    "reasoning": "justificación concisa en 1 oración",
    "recommended_price_range": "rango en USD, ej: $29–$79"
  }
]

Si no podés clasificar con confianza, usá "digital-product" como fallback."""


class ClaudeProductDiscoveryAdapter(ProductDiscoveryPort):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def classify(
        self, opportunities: list[ProductOpportunity]
    ) -> list[ProductClassification]:
        if not opportunities:
            return []

        prompt = self._build_prompt(opportunities)

        try:
            response = await self._client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2000,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            raw_text = response.content[0].text.strip()
            return self._parse_response(raw_text, opportunities)
        except Exception:
            logger.exception("ClaudeProductDiscoveryAdapter.classify failed")
            return [_FALLBACK_CLASSIFICATION] * len(opportunities)

    def _build_prompt(self, opportunities: list[ProductOpportunity]) -> str:
        lines = ["Clasificá cada una de estas oportunidades de producto:\n"]
        for opp in opportunities:
            lines.append(f"- topic: {opp.topic}")
            lines.append(f"  frustration_level: {opp.score.frustration_level:.2f}/10")
            lines.append(f"  competition_gap: {opp.score.competition_gap:.2f}/10")
            lines.append(f"  willingness_to_pay: {opp.score.willingness_to_pay:.2f}/10")
            lines.append(f"  market_size: {opp.score.market_size:.2f}/10")
            lines.append("")
        return "\n".join(lines)

    def _parse_response(
        self, raw_text: str, opportunities: list[ProductOpportunity]
    ) -> list[ProductClassification]:
        try:
            # Strip markdown code fences if present
            text = raw_text
            if text.startswith("```"):
                lines = text.splitlines()
                # Remove first and last fence lines
                text = "\n".join(
                    line for line in lines if not line.startswith("```")
                )

            data = json.loads(text)
            if not isinstance(data, list):
                raise ValueError("Expected a JSON array")

            # Build a lookup by topic for resilience against ordering changes
            by_topic: dict[str, dict] = {
                item["topic"]: item for item in data if isinstance(item, dict)
            }

            results: list[ProductClassification] = []
            for opp in opportunities:
                item = by_topic.get(opp.topic)
                if item is None:
                    logger.warning(
                        "ClaudeProductDiscoveryAdapter: no classification for topic '%s'",
                        opp.topic,
                    )
                    results.append(_FALLBACK_CLASSIFICATION)
                    continue

                raw_type = item.get("product_type", "digital-product")
                try:
                    product_type = ProductType(raw_type)
                except ValueError:
                    logger.warning(
                        "ClaudeProductDiscoveryAdapter: unknown product_type '%s'", raw_type
                    )
                    product_type = ProductType.DIGITAL_PRODUCT

                results.append(
                    ProductClassification(
                        product_type=product_type,
                        reasoning=item.get("reasoning", ""),
                        recommended_price_range=item.get(
                            "recommended_price_range", "$29–$99"
                        ),
                    )
                )
            return results

        except Exception:
            logger.exception(
                "ClaudeProductDiscoveryAdapter: failed to parse Claude response"
            )
            return [_FALLBACK_CLASSIFICATION] * len(opportunities)

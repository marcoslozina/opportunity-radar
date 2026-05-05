from __future__ import annotations

import anthropic

from config import settings
from domain.entities.opportunity import Opportunity
from domain.ports.insight_port import InsightPort

_SYSTEM_PROMPT = """Sos un experto en marketing de contenido para creators e indie makers.
Tu tarea es analizar oportunidades de mercado y generar una acción concreta y específica para cada una.
La acción debe ser ejecutable esta semana. Máximo 15 palabras por acción."""


class ClaudeInsightAdapter(InsightPort):
    def __init__(self) -> None:
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    async def synthesize(self, opportunities: list[Opportunity], discovery_mode: str) -> None:
        if not opportunities:
            return

        system_prompt = _SYSTEM_PROMPT
        if discovery_mode == "real_estate":
            system_prompt += (
                "\n\nMODO PROPFLOW: Para cada oportunidad, además de la acción, clasificá su aplicabilidad "
                "usando exactamente uno de estos valores: [calculadora, contenido, feature, irrelevante] "
                "y dános un razonamiento breve. Respondé en formato CSV: Acción|Aplicabilidad|Razonamiento"
            )
        elif discovery_mode == "esg_intelligence":
            system_prompt += (
                "\n\nMODO ESG: Para cada oportunidad, además de la acción, clasificá su implicación "
                "usando exactamente uno de estos valores: [feature, contenido, posicionamiento, irrelevante] "
                "y dános un razonamiento breve. Respondé en formato CSV: Acción|Implicación|Razonamiento"
            )

        topics_text = "\n".join(
            f"{i + 1}. {opp.topic} (score: {opp.score.total:.0f}/100)"
            for i, opp in enumerate(opportunities)
        )

        response = self._client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1024,
            system=[
                {"type": "text", "text": system_prompt},
                {
                    "type": "text",
                    "text": "Respondé UNICAMENTE con una línea por oportunidad, usando el separador |.",
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=[
                {
                    "role": "user",
                    "content": f"Analizá estas oportunidades:\n{topics_text}",
                }
            ],
        )

        raw = response.content[0].text.strip()
        lines = [line.strip() for line in raw.splitlines() if line.strip()]

        for i, opp in enumerate(opportunities):
            if i < len(lines):
                parts = [p.strip() for p in lines[i].split("|")]
                opp.recommended_action = parts[0]
                if len(parts) >= 2:
                    opp.domain_applicability = parts[1]
                if len(parts) >= 3:
                    opp.domain_reasoning = parts[2]
            else:
                opp.recommended_action = "Crear contenido sobre este tema"

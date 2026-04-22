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

    async def synthesize(self, opportunities: list[Opportunity]) -> list[str]:
        if not opportunities:
            return []

        topics_text = "\n".join(
            f"{i + 1}. {opp.topic} (score: {opp.score.total:.0f}/100)"
            for i, opp in enumerate(opportunities)
        )

        response = self._client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=[
                {"type": "text", "text": _SYSTEM_PROMPT},
                {
                    "type": "text",
                    "text": "Respondé SOLO con una acción por línea, sin numeración ni explicaciones.",
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=[
                {
                    "role": "user",
                    "content": f"Generá una acción recomendada para cada oportunidad:\n{topics_text}",
                }
            ],
        )

        raw = response.content[0].text.strip()
        actions = [line.strip() for line in raw.splitlines() if line.strip()]

        # garantizar misma cantidad que opportunities
        while len(actions) < len(opportunities):
            actions.append("Crear contenido sobre este tema esta semana")

        return actions[: len(opportunities)]

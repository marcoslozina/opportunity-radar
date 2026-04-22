from __future__ import annotations

from datetime import datetime, timezone

from serpapi import GoogleSearch

from config import settings
from domain.ports.trend_data_port import TrendDataPort
from domain.value_objects.trend_signal import TrendSignal


class SerpAdapter(TrendDataPort):
    async def collect(self, keywords: list[str]) -> list[TrendSignal]:
        if not settings.serp_api_key:
            return []
        signals: list[TrendSignal] = []
        for keyword in keywords:
            signals.extend(self._fetch(keyword))
        return signals

    def _fetch(self, keyword: str) -> list[TrendSignal]:
        try:
            search = GoogleSearch({"q": keyword, "api_key": settings.serp_api_key})
            results = search.get_dict()

            signals: list[TrendSignal] = []
            now = datetime.now(tz=timezone.utc)

            # competition_gap: invertido — menos resultados orgánicos = más gap
            organic = results.get("organic_results", [])
            competition_raw = 1.0 - min(len(organic) / 10, 1.0)
            signals.append(
                TrendSignal(
                    source="serp",
                    topic=keyword,
                    raw_value=competition_raw,
                    signal_type="competition_gap",
                    collected_at=now,
                )
            )

            # monetization_intent: presencia de ads = intención comercial alta
            ads = results.get("ads", [])
            monetization_raw = min(len(ads) / 5, 1.0)
            signals.append(
                TrendSignal(
                    source="serp",
                    topic=keyword,
                    raw_value=monetization_raw,
                    signal_type="monetization_intent",
                    collected_at=now,
                )
            )
            return signals
        except Exception:
            return []

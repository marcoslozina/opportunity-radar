from __future__ import annotations

from datetime import datetime, timezone

import httpx

from domain.ports.trend_data_port import TrendDataPort
from domain.value_objects.trend_signal import TrendSignal

_HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"


class HackerNewsAdapter(TrendDataPort):
    async def collect(self, keywords: list[str]) -> list[TrendSignal]:
        signals: list[TrendSignal] = []
        async with httpx.AsyncClient(timeout=10) as client:
            for keyword in keywords:
                signals.extend(await self._fetch(client, keyword))
        return signals

    async def _fetch(self, client: httpx.AsyncClient, keyword: str) -> list[TrendSignal]:
        try:
            resp = await client.get(_HN_SEARCH_URL, params={"query": keyword, "tags": "story"})
            resp.raise_for_status()
            data = resp.json()
            hits = data.get("hits", [])
            if not hits:
                return []
            # raw_value: ratio de puntos promedio normalizado a 0–1 (cap 500 pts)
            avg_points = sum(h.get("points", 0) for h in hits) / len(hits)
            raw_value = min(avg_points / 500, 1.0)
            return [
                TrendSignal(
                    source="hacker_news",
                    topic=keyword,
                    raw_value=raw_value,
                    signal_type="social_signal",
                    collected_at=datetime.now(tz=timezone.utc),
                )
            ]
        except Exception:
            return []

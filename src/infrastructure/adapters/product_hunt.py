from __future__ import annotations

from datetime import datetime, timezone

import httpx

from config import settings
from domain.ports.trend_data_port import TrendDataPort
from domain.value_objects.trend_signal import TrendSignal

_PH_API_URL = "https://api.producthunt.com/v2/api/graphql"

_QUERY = """
query($query: String!) {
  posts(topic: $query, order: VOTES, first: 10) {
    edges {
      node {
        votesCount
      }
    }
  }
}
"""


class ProductHuntAdapter(TrendDataPort):
    async def collect(self, keywords: list[str]) -> list[TrendSignal]:
        if not settings.product_hunt_token:
            return []
        signals: list[TrendSignal] = []
        async with httpx.AsyncClient(timeout=10) as client:
            for keyword in keywords:
                signal = await self._fetch(client, keyword)
                if signal:
                    signals.append(signal)
        return signals

    async def _fetch(self, client: httpx.AsyncClient, keyword: str) -> TrendSignal | None:
        try:
            resp = await client.post(
                _PH_API_URL,
                json={"query": _QUERY, "variables": {"query": keyword}},
                headers={"Authorization": f"Bearer {settings.product_hunt_token}"},
            )
            resp.raise_for_status()
            edges = resp.json().get("data", {}).get("posts", {}).get("edges", [])
            if not edges:
                return None
            avg_votes = sum(e["node"]["votesCount"] for e in edges) / len(edges)
            raw_value = min(avg_votes / 500, 1.0)
            return TrendSignal(
                source="product_hunt",
                topic=keyword,
                raw_value=raw_value,
                signal_type="monetization_intent",
                collected_at=datetime.now(tz=timezone.utc),
            )
        except Exception:
            return None

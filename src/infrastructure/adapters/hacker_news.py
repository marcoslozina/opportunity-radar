from __future__ import annotations

from datetime import datetime, timezone

import httpx

from domain.ports.trend_data_port import TrendDataPort
from domain.value_objects.evidence_item import EvidenceItem
from domain.value_objects.trend_signal import TrendSignal

_HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"


class HackerNewsAdapter(TrendDataPort):
    def __init__(self) -> None:
        self._last_evidence: list[EvidenceItem] = []

    async def collect(self, keywords: list[str]) -> list[TrendSignal]:
        signals: list[TrendSignal] = []
        all_evidence: list[EvidenceItem] = []
        async with httpx.AsyncClient(timeout=10) as client:
            for keyword in keywords:
                batch_signals, batch_evidence = await self._fetch(client, keyword)
                signals.extend(batch_signals)
                all_evidence.extend(batch_evidence)
        self._last_evidence = all_evidence
        return signals

    async def _fetch(self, client: httpx.AsyncClient, keyword: str) -> tuple[list[TrendSignal], list[EvidenceItem]]:
        try:
            resp = await client.get(_HN_SEARCH_URL, params={"query": keyword, "tags": "story"})
            resp.raise_for_status()
            data = resp.json()
            hits = data.get("hits", [])
            if not hits:
                return [], []
            # raw_value: ratio de puntos promedio normalizado a 0–1 (cap 500 pts)
            avg_points = sum(h.get("points", 0) for h in hits) / len(hits)
            raw_value = min(avg_points / 500, 1.0)
            signals = [
                TrendSignal(
                    source="hacker_news",
                    topic=keyword,
                    raw_value=raw_value,
                    signal_type="social_signal",
                    collected_at=datetime.now(tz=timezone.utc),
                )
            ]
            evidence = self._collect_evidence(keyword, hits)
            return signals, evidence
        except Exception:
            return [], []

    def _collect_evidence(self, keyword: str, hits: list[dict]) -> list[EvidenceItem]:
        try:
            now = datetime.now(tz=timezone.utc)
            items = [
                EvidenceItem(
                    source="hacker_news",
                    signal_type="social_signal",
                    topic=keyword,
                    title=hit.get("title", ""),
                    url=hit.get("url"),  # may be None for Ask HN posts
                    engagement_count=hit.get("points", 0),
                    engagement_label="points",
                    collected_at=now,
                )
                for hit in hits
                if hit.get("title") and hit.get("points", 0) > 0
            ]
            return sorted(items, key=lambda e: e.engagement_count, reverse=True)[:5]
        except Exception:
            return []

from __future__ import annotations

from datetime import datetime, timezone

from serpapi import Client

from config import settings
from domain.ports.trend_data_port import TrendDataPort
from domain.value_objects.evidence_item import EvidenceItem
from domain.value_objects.trend_signal import TrendSignal


class SerpAdapter(TrendDataPort):
    def __init__(self) -> None:
        self._last_evidence: list[EvidenceItem] = []

    async def collect(self, keywords: list[str]) -> list[TrendSignal]:
        if not settings.serp_api_key:
            return []
        signals: list[TrendSignal] = []
        all_evidence: list[EvidenceItem] = []
        for keyword in keywords:
            batch_signals, batch_evidence = self._fetch(keyword)
            signals.extend(batch_signals)
            all_evidence.extend(batch_evidence)
        self._last_evidence = all_evidence
        return signals

    def _fetch(self, keyword: str) -> tuple[list[TrendSignal], list[EvidenceItem]]:
        try:
            client = Client(api_key=settings.serp_api_key)
            results = client.search({"engine": "google", "q": keyword})

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

            evidence = self._collect_evidence(keyword, results)
            return signals, evidence
        except Exception:
            return [], []

    def _collect_evidence(self, keyword: str, results: dict) -> list[EvidenceItem]:
        try:
            now = datetime.now(tz=timezone.utc)
            evidence: list[EvidenceItem] = []

            organic = results.get("organic_results", [])
            for i, result in enumerate(organic[:5]):
                evidence.append(EvidenceItem(
                    source="serp",
                    signal_type="competition_gap",
                    topic=keyword,
                    title=result.get("title", ""),
                    url=result.get("link"),
                    engagement_count=max(10 - i, 1),  # rank inverted: position 0 → count 10
                    engagement_label="rank",
                    collected_at=now,
                ))

            ads = results.get("ads", [])
            for i, ad in enumerate(ads[:5]):
                evidence.append(EvidenceItem(
                    source="serp",
                    signal_type="monetization_intent",
                    topic=keyword,
                    title=ad.get("title", ""),
                    url=ad.get("link"),
                    engagement_count=max(5 - i, 1),  # ad position inverted
                    engagement_label="ad_position",
                    collected_at=now,
                ))

            return evidence
        except Exception:
            return []

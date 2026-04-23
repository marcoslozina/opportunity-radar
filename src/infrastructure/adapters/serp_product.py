from __future__ import annotations

import logging
from datetime import datetime, timezone

from serpapi import Client

from config import Settings
from domain.ports.trend_data_port import TrendDataPort
from domain.value_objects.trend_signal import TrendSignal

logger = logging.getLogger(__name__)

_MAX_RESULTS = 10_000_000


class SerpProductAdapter(TrendDataPort):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def collect(self, keywords: list[str]) -> list[TrendSignal]:
        if not self._settings.serp_api_key:
            return []
        signals: list[TrendSignal] = []
        for keyword in keywords:
            signal = self._fetch(keyword)
            if signal is not None:
                signals.append(signal)
        return signals

    def _fetch(self, keyword: str) -> TrendSignal | None:
        queries = [
            f"{keyword} software",
            f"{keyword} tool",
            f"alternatives to {keyword}",
        ]
        total_results_list: list[int] = []

        for query in queries:
            try:
                client = Client(api_key=self._settings.serp_api_key)
                results = client.search({"engine": "google", "q": query})
                organic = results.get("organic_results", [])
                # Prefer total_results from search_information if available
                search_info = results.get("search_information", {})
                total_results = search_info.get("total_results", len(organic))
                total_results_list.append(int(total_results))
            except Exception:
                logger.exception(
                    "SerpProductAdapter failed for query '%s'", query
                )

        if not total_results_list:
            return None

        avg_results = sum(total_results_list) / len(total_results_list)
        raw_value = min(avg_results, _MAX_RESULTS) / _MAX_RESULTS

        return TrendSignal(
            source="serp_product",
            topic=keyword,
            raw_value=raw_value,
            signal_type="competition_gap",
            collected_at=datetime.now(tz=timezone.utc),
        )

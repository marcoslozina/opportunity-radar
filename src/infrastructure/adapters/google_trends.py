from __future__ import annotations

from datetime import datetime, timezone

from cachetools import TTLCache
from pytrends.request import TrendReq

from domain.ports.trend_data_port import TrendDataPort
from domain.value_objects.trend_signal import TrendSignal

_cache: TTLCache[str, float] = TTLCache(maxsize=256, ttl=3600)


class GoogleTrendsAdapter(TrendDataPort):
    def __init__(self) -> None:
        self._pytrends = TrendReq(hl="en-US", tz=360)

    async def collect(self, keywords: list[str]) -> list[TrendSignal]:
        signals: list[TrendSignal] = []
        for keyword in keywords:
            raw_value = self._fetch(keyword)
            if raw_value is not None:
                signals.append(
                    TrendSignal(
                        source="google_trends",
                        topic=keyword,
                        raw_value=raw_value,
                        signal_type="trend_velocity",
                        collected_at=datetime.now(tz=timezone.utc),
                    )
                )
        return signals

    def _fetch(self, keyword: str) -> float | None:
        if keyword in _cache:
            return _cache[keyword]
        try:
            self._pytrends.build_payload([keyword], timeframe="today 3-m")
            df = self._pytrends.interest_over_time()
            if df.empty or keyword not in df.columns:
                return None
            # último valor normalizado a 0–1 (Google Trends ya da 0–100)
            raw_value = float(df[keyword].iloc[-1]) / 100.0
            _cache[keyword] = raw_value
            return raw_value
        except Exception:
            return None

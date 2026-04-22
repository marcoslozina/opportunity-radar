from __future__ import annotations

from datetime import datetime, timezone

from googleapiclient.discovery import build

from config import settings
from domain.ports.trend_data_port import TrendDataPort
from domain.value_objects.trend_signal import TrendSignal


class YouTubeAdapter(TrendDataPort):
    async def collect(self, keywords: list[str]) -> list[TrendSignal]:
        if not settings.youtube_api_key:
            return []
        signals: list[TrendSignal] = []
        try:
            service = build("youtube", "v3", developerKey=settings.youtube_api_key)
            for keyword in keywords:
                signal = self._fetch(service, keyword)
                if signal:
                    signals.append(signal)
        except Exception:
            pass
        return signals

    def _fetch(self, service: object, keyword: str) -> TrendSignal | None:
        try:
            request = service.search().list(  # type: ignore[attr-defined]
                q=keyword,
                part="snippet",
                type="video",
                order="viewCount",
                maxResults=10,
                publishedAfter="2024-01-01T00:00:00Z",
            )
            response = request.execute()
            items = response.get("items", [])
            if not items:
                return None
            # raw_value basado en cantidad de resultados relevantes (cap 10)
            raw_value = len(items) / 10.0
            return TrendSignal(
                source="youtube",
                topic=keyword,
                raw_value=raw_value,
                signal_type="social_signal",
                collected_at=datetime.now(tz=timezone.utc),
            )
        except Exception:
            return None

from __future__ import annotations

from datetime import datetime, timezone

from googleapiclient.discovery import build

from config import settings
from domain.ports.trend_data_port import TrendDataPort
from domain.value_objects.evidence_item import EvidenceItem
from domain.value_objects.trend_signal import TrendSignal


class YouTubeAdapter(TrendDataPort):
    def __init__(self) -> None:
        self._last_evidence: list[EvidenceItem] = []

    async def collect(self, keywords: list[str]) -> list[TrendSignal]:
        if not settings.youtube_api_key:
            return []
        signals: list[TrendSignal] = []
        all_evidence: list[EvidenceItem] = []
        try:
            service = build("youtube", "v3", developerKey=settings.youtube_api_key)
            for keyword in keywords:
                signal, evidence = self._fetch(service, keyword)
                if signal:
                    signals.append(signal)
                all_evidence.extend(evidence)
        except Exception:
            pass
        self._last_evidence = all_evidence
        return signals

    def _fetch(self, service: object, keyword: str) -> tuple[TrendSignal | None, list[EvidenceItem]]:
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
                return None, []
            # raw_value basado en cantidad de resultados relevantes (cap 10)
            raw_value = len(items) / 10.0
            signal = TrendSignal(
                source="youtube",
                topic=keyword,
                raw_value=raw_value,
                signal_type="social_signal",
                collected_at=datetime.now(tz=timezone.utc),
            )
            evidence = self._collect_evidence(keyword, items)
            return signal, evidence
        except Exception:
            return None, []

    def _collect_evidence(self, keyword: str, items: list[dict]) -> list[EvidenceItem]:
        try:
            now = datetime.now(tz=timezone.utc)
            return [
                EvidenceItem(
                    source="youtube",
                    signal_type="social_signal",
                    topic=keyword,
                    title=item["snippet"]["title"],
                    url=f"https://youtube.com/watch?v={item['id']['videoId']}",
                    engagement_count=max(len(items) - i, 1),  # rank: first result = highest
                    engagement_label="search_rank",
                    collected_at=now,
                )
                for i, item in enumerate(items)
                if item.get("snippet", {}).get("title") and item.get("id", {}).get("videoId")
            ]
        except Exception:
            return []

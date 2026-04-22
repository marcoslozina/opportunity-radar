from __future__ import annotations

from datetime import datetime, timezone

import praw
import praw.exceptions

from config import settings
from domain.ports.trend_data_port import TrendDataPort
from domain.value_objects.trend_signal import TrendSignal


class RedditAdapter(TrendDataPort):
    def __init__(self) -> None:
        self._reddit = praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent,
        )

    async def collect(self, keywords: list[str]) -> list[TrendSignal]:
        signals: list[TrendSignal] = []
        for keyword in keywords:
            signals.extend(self._fetch(keyword))
        return signals

    def _fetch(self, keyword: str) -> list[TrendSignal]:
        try:
            results = list(self._reddit.subreddit("all").search(keyword, limit=25, time_filter="week"))
            if not results:
                return []
            avg_score = sum(p.score for p in results) / len(results)
            raw_value = min(avg_score / 1000, 1.0)
            return [
                TrendSignal(
                    source="reddit",
                    topic=keyword,
                    raw_value=raw_value,
                    signal_type="social_signal",
                    collected_at=datetime.now(tz=timezone.utc),
                )
            ]
        except Exception:
            return []

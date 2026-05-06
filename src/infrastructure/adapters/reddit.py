from __future__ import annotations

from datetime import datetime, timezone

import praw
import praw.exceptions

from config import settings
from domain.ports.trend_data_port import TrendDataPort
from domain.value_objects.evidence_item import EvidenceItem
from domain.value_objects.trend_signal import TrendSignal


class RedditAdapter(TrendDataPort):
    def __init__(self) -> None:
        self._reddit = praw.Reddit(
            client_id=settings.reddit_client_id,
            client_secret=settings.reddit_client_secret,
            user_agent=settings.reddit_user_agent,
        )
        self._last_evidence: list[EvidenceItem] = []

    async def collect(self, keywords: list[str]) -> list[TrendSignal]:
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
            results = list(self._reddit.subreddit("all").search(keyword, limit=25, time_filter="week"))
            if not results:
                return [], []
            avg_score = sum(p.score for p in results) / len(results)
            raw_value = min(avg_score / 1000, 1.0)
            signals = [
                TrendSignal(
                    source="reddit",
                    topic=keyword,
                    raw_value=raw_value,
                    signal_type="social_signal",
                    collected_at=datetime.now(tz=timezone.utc),
                )
            ]
            evidence = self._collect_evidence(keyword, results)
            return signals, evidence
        except Exception:
            return [], []

    def _collect_evidence(self, keyword: str, posts: list) -> list[EvidenceItem]:
        try:
            now = datetime.now(tz=timezone.utc)
            items = [
                EvidenceItem(
                    source="reddit",
                    signal_type="social_signal",
                    topic=keyword,
                    title=post.title,
                    url=f"https://reddit.com{post.permalink}",
                    engagement_count=post.score,
                    engagement_label="upvotes",
                    collected_at=now,
                )
                for post in posts
                if post.title and post.score > 0
            ]
            return sorted(items, key=lambda e: e.engagement_count, reverse=True)[:5]
        except Exception:
            return []

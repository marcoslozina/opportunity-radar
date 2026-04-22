from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx
import praw

from config import Settings
from domain.ports.trend_data_port import TrendDataPort
from domain.value_objects.trend_signal import TrendSignal

logger = logging.getLogger(__name__)

_HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"

_QUERY_PATTERNS = [
    "is there a tool for {kw}",
    "why is there no {kw}",
    "I do this manually {kw}",
    "pain with {kw}",
]


class RedditFrustrationAdapter(TrendDataPort):
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._reddit: praw.Reddit | None = None
        if settings.reddit_client_id and settings.reddit_client_secret:
            self._reddit = praw.Reddit(
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                user_agent=settings.reddit_user_agent,
            )

    async def collect(self, keywords: list[str]) -> list[TrendSignal]:
        if self._reddit is None:
            return []
        signals: list[TrendSignal] = []
        for keyword in keywords:
            signal = self._fetch(keyword)
            if signal is not None:
                signals.append(signal)
        return signals

    def _fetch(self, keyword: str) -> TrendSignal | None:
        try:
            subreddit = self._reddit.subreddit("all")  # type: ignore[union-attr]
            all_posts: list[praw.models.Submission] = []
            for pattern in _QUERY_PATTERNS:
                query = pattern.format(kw=keyword)
                posts = list(subreddit.search(query, limit=25))
                all_posts.extend(posts)

            if not all_posts:
                return None

            avg_score = sum(min(p.score, 1000) / 1000 for p in all_posts) / len(all_posts)
            return TrendSignal(
                source="reddit_frustration",
                topic=keyword,
                raw_value=avg_score,
                signal_type="frustration_level",
                collected_at=datetime.now(tz=timezone.utc),
            )
        except Exception:
            logger.exception("RedditFrustrationAdapter failed for keyword '%s'", keyword)
            return None


class HNFrustrationAdapter(TrendDataPort):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def collect(self, keywords: list[str]) -> list[TrendSignal]:
        if self._client is not None:
            return await self._collect_with(self._client, keywords)
        async with httpx.AsyncClient(timeout=10) as client:
            return await self._collect_with(client, keywords)

    async def _collect_with(
        self, client: httpx.AsyncClient, keywords: list[str]
    ) -> list[TrendSignal]:
        signals: list[TrendSignal] = []
        for keyword in keywords:
            signal = await self._fetch(client, keyword)
            if signal is not None:
                signals.append(signal)
        return signals

    async def _fetch(
        self, client: httpx.AsyncClient, keyword: str
    ) -> TrendSignal | None:
        try:
            all_hits: list[dict] = []
            for pattern in _QUERY_PATTERNS:
                query = pattern.format(kw=keyword)
                resp = await client.get(
                    _HN_SEARCH_URL,
                    params={"query": query, "tags": "ask_hn,show_hn", "hitsPerPage": 25},
                )
                resp.raise_for_status()
                data = resp.json()
                all_hits.extend(data.get("hits", []))

            if not all_hits:
                return None

            avg_value = sum(
                min(hit.get("points", 0), 500) / 500 for hit in all_hits
            ) / len(all_hits)
            return TrendSignal(
                source="hn_frustration",
                topic=keyword,
                raw_value=avg_value,
                signal_type="frustration_level",
                collected_at=datetime.now(tz=timezone.utc),
            )
        except Exception:
            logger.exception("HNFrustrationAdapter failed for keyword '%s'", keyword)
            return None

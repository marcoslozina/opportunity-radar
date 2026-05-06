from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from domain.value_objects.evidence_item import EvidenceItem

_NOW = datetime.now(tz=timezone.utc)


# ─── Reddit ──────────────────────────────────────────────────────────────────

class TestRedditEvidenceCollection:
    def _make_adapter(self):
        """Create RedditAdapter without hitting Reddit API."""
        with patch("infrastructure.adapters.reddit.praw.Reddit"):
            from infrastructure.adapters.reddit import RedditAdapter
            return RedditAdapter()

    def _make_post(self, title: str, score: int, permalink: str = "/r/test/abc") -> MagicMock:
        post = MagicMock()
        post.title = title
        post.score = score
        post.permalink = permalink
        return post

    def test_collect_evidence_returns_top5_by_score(self) -> None:
        adapter = self._make_adapter()
        posts = [self._make_post(f"Post {i}", score) for i, score in enumerate([800, 650, 400, 320, 200, 150, 80, 30])]
        result = adapter._collect_evidence("test", posts)
        assert len(result) == 5
        assert [e.engagement_count for e in result] == [800, 650, 400, 320, 200]

    def test_collect_evidence_empty_when_no_posts(self) -> None:
        adapter = self._make_adapter()
        result = adapter._collect_evidence("test", [])
        assert result == []

    def test_collect_evidence_filters_zero_score_posts(self) -> None:
        adapter = self._make_adapter()
        posts = [
            self._make_post("Good post", 100),
            self._make_post("Zero score", 0),
        ]
        result = adapter._collect_evidence("test", posts)
        assert len(result) == 1
        assert result[0].engagement_count == 100

    def test_collect_evidence_correct_fields(self) -> None:
        adapter = self._make_adapter()
        post = self._make_post("Great Post", 500, "/r/test/comments/xyz")
        result = adapter._collect_evidence("angular signals", [post])
        assert len(result) == 1
        item = result[0]
        assert item.source == "reddit"
        assert item.signal_type == "social_signal"
        assert item.engagement_label == "upvotes"
        assert item.url == "https://reddit.com/r/test/comments/xyz"
        assert item.topic == "angular signals"

    def test_collect_evidence_returns_empty_on_exception(self) -> None:
        adapter = self._make_adapter()
        broken_post = MagicMock()
        broken_post.title = "ok"
        broken_post.score = 100
        type(broken_post).permalink = property(lambda self: (_ for _ in ()).throw(RuntimeError("broken")))
        result = adapter._collect_evidence("test", [broken_post])
        assert result == []


# ─── HackerNews ──────────────────────────────────────────────────────────────

class TestHackerNewsEvidenceCollection:
    def _make_adapter(self):
        from infrastructure.adapters.hacker_news import HackerNewsAdapter
        return HackerNewsAdapter()

    def test_collect_evidence_returns_top5_by_points(self) -> None:
        adapter = self._make_adapter()
        hits = [
            {"title": f"Story {i}", "points": pts, "url": f"https://example.com/{i}"}
            for i, pts in enumerate([500, 400, 300, 200, 150, 100, 50])
        ]
        result = adapter._collect_evidence("test", hits)
        assert len(result) == 5
        assert [e.engagement_count for e in result] == [500, 400, 300, 200, 150]

    def test_collect_evidence_url_nullable_for_ask_posts(self) -> None:
        adapter = self._make_adapter()
        hits = [{"title": "Ask HN: something", "points": 200, "url": None}]
        result = adapter._collect_evidence("ask hn", hits)
        assert len(result) == 1
        assert result[0].url is None

    def test_collect_evidence_filters_zero_points(self) -> None:
        adapter = self._make_adapter()
        hits = [
            {"title": "Good story", "points": 150, "url": "https://example.com"},
            {"title": "No points story", "points": 0, "url": "https://example.com/2"},
        ]
        result = adapter._collect_evidence("test", hits)
        assert len(result) == 1
        assert result[0].engagement_label == "points"
        assert result[0].source == "hacker_news"

    def test_collect_evidence_empty_on_no_hits(self) -> None:
        adapter = self._make_adapter()
        result = adapter._collect_evidence("test", [])
        assert result == []


# ─── SERP ────────────────────────────────────────────────────────────────────

class TestSerpEvidenceCollection:
    def _make_adapter(self):
        from infrastructure.adapters.serp import SerpAdapter
        return SerpAdapter()

    def test_collect_evidence_produces_two_signal_types(self) -> None:
        adapter = self._make_adapter()
        results_dict = {
            "organic_results": [
                {"title": f"Organic {i}", "link": f"https://example.com/o{i}"}
                for i in range(3)
            ],
            "ads": [
                {"title": f"Ad {i}", "link": f"https://example.com/a{i}"}
                for i in range(2)
            ],
        }
        result = adapter._collect_evidence("test keyword", results_dict)
        signal_types = {e.signal_type for e in result}
        assert "competition_gap" in signal_types
        assert "monetization_intent" in signal_types

    def test_collect_evidence_organic_uses_rank_inverted(self) -> None:
        adapter = self._make_adapter()
        results_dict = {
            "organic_results": [
                {"title": "First", "link": "https://example.com/1"},
                {"title": "Second", "link": "https://example.com/2"},
            ],
            "ads": [],
        }
        result = adapter._collect_evidence("test", results_dict)
        organic = sorted([e for e in result if e.signal_type == "competition_gap"], key=lambda e: e.engagement_count, reverse=True)
        assert organic[0].engagement_count == 10  # position 0 → 10 - 0 = 10
        assert organic[1].engagement_count == 9   # position 1 → 10 - 1 = 9

    def test_collect_evidence_ads_engagement_label(self) -> None:
        adapter = self._make_adapter()
        results_dict = {
            "organic_results": [],
            "ads": [{"title": "Ad 1", "link": "https://ads.com/1"}],
        }
        result = adapter._collect_evidence("test", results_dict)
        ad_items = [e for e in result if e.signal_type == "monetization_intent"]
        assert len(ad_items) == 1
        assert ad_items[0].engagement_label == "ad_position"
        assert ad_items[0].source == "serp"

    def test_collect_evidence_caps_at_5_per_stream(self) -> None:
        adapter = self._make_adapter()
        results_dict = {
            "organic_results": [{"title": f"O{i}", "link": f"https://e.com/{i}"} for i in range(10)],
            "ads": [{"title": f"A{i}", "link": f"https://a.com/{i}"} for i in range(10)],
        }
        result = adapter._collect_evidence("test", results_dict)
        organic = [e for e in result if e.signal_type == "competition_gap"]
        ads = [e for e in result if e.signal_type == "monetization_intent"]
        assert len(organic) == 5
        assert len(ads) == 5


# ─── YouTube ─────────────────────────────────────────────────────────────────

class TestYouTubeEvidenceCollection:
    def _make_adapter(self):
        from infrastructure.adapters.youtube import YouTubeAdapter
        return YouTubeAdapter()

    def test_collect_evidence_builds_url_from_video_id(self) -> None:
        adapter = self._make_adapter()
        items = [
            {"snippet": {"title": "Test Video"}, "id": {"videoId": "abc123"}},
        ]
        result = adapter._collect_evidence("test", items)
        assert len(result) == 1
        assert result[0].url == "https://youtube.com/watch?v=abc123"

    def test_collect_evidence_rank_inverted(self) -> None:
        adapter = self._make_adapter()
        items = [
            {"snippet": {"title": f"Video {i}"}, "id": {"videoId": f"id{i}"}}
            for i in range(3)
        ]
        result = adapter._collect_evidence("test", items)
        # index 0 → count = 3, index 1 → count = 2, index 2 → count = 1
        assert result[0].engagement_count == 3
        assert result[1].engagement_count == 2
        assert result[2].engagement_count == 1

    def test_collect_evidence_filters_missing_video_id(self) -> None:
        adapter = self._make_adapter()
        items = [
            {"snippet": {"title": "Valid video"}, "id": {"videoId": "abc"}},
            {"snippet": {"title": "No id video"}, "id": {}},  # missing videoId
        ]
        result = adapter._collect_evidence("test", items)
        assert len(result) == 1
        assert result[0].url == "https://youtube.com/watch?v=abc"

    def test_collect_evidence_correct_fields(self) -> None:
        adapter = self._make_adapter()
        items = [{"snippet": {"title": "Angular Tutorial"}, "id": {"videoId": "xyz789"}}]
        result = adapter._collect_evidence("angular", items)
        assert result[0].source == "youtube"
        assert result[0].signal_type == "social_signal"
        assert result[0].engagement_label == "search_rank"
        assert result[0].topic == "angular"

from __future__ import annotations

import httpx
import pytest
import respx

from config import Settings
from infrastructure.adapters.frustration_signal import HNFrustrationAdapter, _HN_SEARCH_URL, RedditFrustrationAdapter


@pytest.fixture
def hits_with_points() -> list[dict]:
    return [{"points": 100}, {"points": 200}, {"points": 50}]


async def test_hn_frustration_returns_signals(hits_with_points: list[dict]) -> None:
    with respx.mock:
        respx.get(_HN_SEARCH_URL).mock(
            return_value=httpx.Response(200, json={"hits": hits_with_points})
        )
        adapter = HNFrustrationAdapter()
        signals = await adapter.collect(["python testing"])

    assert len(signals) == 1
    assert signals[0].source == "hn_frustration"
    assert signals[0].signal_type == "frustration_level"
    assert 0.0 <= signals[0].raw_value <= 1.0


async def test_hn_frustration_returns_empty_on_no_hits() -> None:
    with respx.mock:
        respx.get(_HN_SEARCH_URL).mock(
            return_value=httpx.Response(200, json={"hits": []})
        )
        adapter = HNFrustrationAdapter()
        signals = await adapter.collect(["completely obscure topic xyz"])

    assert signals == []


async def test_reddit_frustration_returns_empty_without_credentials() -> None:
    settings = Settings(
        reddit_client_id="",
        reddit_client_secret="",
    )
    adapter = RedditFrustrationAdapter(settings)
    signals = await adapter.collect(["python testing"])
    assert signals == []

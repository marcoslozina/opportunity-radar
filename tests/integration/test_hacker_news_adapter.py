from __future__ import annotations

import pytest
import respx
import httpx

from infrastructure.adapters.hacker_news import HackerNewsAdapter, _HN_SEARCH_URL


@pytest.fixture
def hn_hits() -> list[dict]:
    return [{"points": 200}, {"points": 400}, {"points": 100}]


async def test_collect_when_hits_found_then_returns_signal(hn_hits: list[dict]) -> None:
    with respx.mock:
        respx.get(_HN_SEARCH_URL).mock(
            return_value=httpx.Response(200, json={"hits": hn_hits})
        )
        adapter = HackerNewsAdapter()
        signals = await adapter.collect(["angular signals"])

    assert len(signals) == 1
    assert signals[0].source == "hacker_news"
    assert signals[0].signal_type == "social_signal"
    assert 0.0 <= signals[0].raw_value <= 1.0


async def test_collect_when_no_hits_then_returns_empty() -> None:
    with respx.mock:
        respx.get(_HN_SEARCH_URL).mock(
            return_value=httpx.Response(200, json={"hits": []})
        )
        adapter = HackerNewsAdapter()
        signals = await adapter.collect(["obscure topic xyz"])

    assert signals == []


async def test_collect_when_api_fails_then_returns_empty() -> None:
    with respx.mock:
        respx.get(_HN_SEARCH_URL).mock(side_effect=httpx.ConnectError("timeout"))
        adapter = HackerNewsAdapter()
        signals = await adapter.collect(["angular"])

    assert signals == []

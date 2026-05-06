from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from domain.value_objects.alert_payload import AlertPayload
from infrastructure.adapters.webhook_notification import WebhookNotificationAdapter


def make_payload() -> AlertPayload:
    return AlertPayload(
        alert_rule_id="rule-123",
        niche_id="niche-456",
        niche_name="Test Niche",
        triggered_at=datetime(2026, 1, 1, 12, 0, 0),
        threshold_score=75.0,
        top_opportunity_topic="AI Tools",
        top_opportunity_score=88.0,
        top_opportunity_trajectory="GROWING ↑",
        top_opportunity_domain_applicability="general",
        top_opportunity_recommended_action="Create content",
    )


async def test_send_alert_to_returns_true_on_success() -> None:
    adapter = WebhookNotificationAdapter()
    payload = make_payload()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("infrastructure.adapters.webhook_notification.httpx.AsyncClient", return_value=mock_client):
        result = await adapter.send_alert_to(payload, "https://example.com/hook")

    assert result is True
    mock_client.post.assert_called_once()
    call_kwargs = mock_client.post.call_args
    assert call_kwargs[0][0] == "https://example.com/hook"


async def test_send_alert_to_returns_false_on_http_error() -> None:
    adapter = WebhookNotificationAdapter()
    payload = make_payload()

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            "500 Internal Server Error",
            request=MagicMock(),
            response=mock_response,
        )
    )

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("infrastructure.adapters.webhook_notification.httpx.AsyncClient", return_value=mock_client):
        result = await adapter.send_alert_to(payload, "https://example.com/hook")

    assert result is False


async def test_send_alert_to_returns_false_on_timeout() -> None:
    adapter = WebhookNotificationAdapter()
    payload = make_payload()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("infrastructure.adapters.webhook_notification.httpx.AsyncClient", return_value=mock_client):
        result = await adapter.send_alert_to(payload, "https://example.com/hook")

    assert result is False


async def test_send_alert_to_returns_false_on_connection_error() -> None:
    adapter = WebhookNotificationAdapter()
    payload = make_payload()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("infrastructure.adapters.webhook_notification.httpx.AsyncClient", return_value=mock_client):
        result = await adapter.send_alert_to(payload, "https://bad.invalid/hook")

    assert result is False


async def test_send_briefing_is_noop() -> None:
    adapter = WebhookNotificationAdapter()
    result = await adapter.send_briefing(object(), "niche-name")
    assert result is False

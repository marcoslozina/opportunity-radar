from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from domain.value_objects.evidence_item import EvidenceItem

_NOW = datetime.now(tz=timezone.utc)


def _make_item(**overrides) -> EvidenceItem:
    defaults = dict(
        source="reddit",
        signal_type="social_signal",
        topic="test topic",
        title="Test Post Title",
        url="https://reddit.com/r/test/comments/abc",
        engagement_count=100,
        engagement_label="upvotes",
        collected_at=_NOW,
    )
    defaults.update(overrides)
    return EvidenceItem(**defaults)


def test_evidence_item_is_immutable() -> None:
    item = _make_item()
    with pytest.raises(FrozenInstanceError):
        item.title = "mutated"  # type: ignore[misc]


def test_evidence_item_requires_all_fields() -> None:
    with pytest.raises(TypeError):
        EvidenceItem(source="reddit")  # type: ignore[call-arg]


def test_evidence_item_url_nullable() -> None:
    item = _make_item(url=None)
    assert item.url is None


def test_evidence_item_stores_all_fields() -> None:
    item = _make_item()
    assert item.source == "reddit"
    assert item.signal_type == "social_signal"
    assert item.topic == "test topic"
    assert item.title == "Test Post Title"
    assert item.engagement_count == 100
    assert item.engagement_label == "upvotes"
    assert item.collected_at == _NOW

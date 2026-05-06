from __future__ import annotations

from datetime import datetime, timezone

from domain.value_objects.evidence_item import EvidenceItem
from infrastructure.db.repositories import _deserialize_evidence, _serialize_evidence

_NOW = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def _make_item(topic: str = "test", url: str | None = "https://example.com") -> EvidenceItem:
    return EvidenceItem(
        source="reddit",
        signal_type="social_signal",
        topic=topic,
        title="Test Post",
        url=url,
        engagement_count=100,
        engagement_label="upvotes",
        collected_at=_NOW,
    )


def test_serialize_evidence_roundtrip() -> None:
    items = [_make_item("topic1"), _make_item("topic2", url=None)]
    serialized = _serialize_evidence(items)
    deserialized = _deserialize_evidence(serialized)
    assert len(deserialized) == 2
    assert deserialized[0].topic == "topic1"
    assert deserialized[0].url == "https://example.com"
    assert deserialized[1].topic == "topic2"
    assert deserialized[1].url is None


def test_serialize_evidence_preserves_datetime() -> None:
    item = _make_item()
    serialized = _serialize_evidence([item])
    deserialized = _deserialize_evidence(serialized)
    assert deserialized[0].collected_at == _NOW


def test_serialize_evidence_empty_list() -> None:
    result = _serialize_evidence([])
    assert result == "[]"


def test_deserialize_evidence_returns_empty_on_invalid_json() -> None:
    result = _deserialize_evidence("not json")
    assert result == []


def test_deserialize_evidence_returns_empty_on_empty_string() -> None:
    result = _deserialize_evidence("")
    assert result == []


def test_deserialize_evidence_returns_empty_on_none_like_value() -> None:
    # server_default="[]" should never produce None, but be safe
    result = _deserialize_evidence("[]")
    assert result == []


def test_deserialize_evidence_returns_empty_on_malformed_item() -> None:
    # JSON array but items missing required fields
    result = _deserialize_evidence('[{"source": "reddit"}]')
    assert result == []

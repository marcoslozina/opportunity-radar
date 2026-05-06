from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from domain.entities.api_key import KEY_PREFIX, ApiKey


def test_generate_returns_raw_key_with_correct_prefix() -> None:
    entity, raw_key = ApiKey.generate(client_name="propflow", scopes=["read:opportunities"])
    assert raw_key.startswith(KEY_PREFIX)


def test_generate_stores_hash_not_raw_key() -> None:
    entity, raw_key = ApiKey.generate(client_name="propflow", scopes=["read:opportunities"])
    assert entity.key_hash != raw_key
    assert len(entity.key_hash) == 64  # SHA-256 hex digest is 64 chars


def test_generate_hash_matches_hash_raw() -> None:
    entity, raw_key = ApiKey.generate(client_name="propflow", scopes=["read:opportunities"])
    assert entity.key_hash == ApiKey.hash_raw(raw_key)


def test_hash_raw_is_deterministic() -> None:
    raw = "or_live_sometoken"
    assert ApiKey.hash_raw(raw) == ApiKey.hash_raw(raw)


def test_hash_raw_different_inputs_differ() -> None:
    assert ApiKey.hash_raw("key_a") != ApiKey.hash_raw("key_b")


def test_is_valid_returns_false_when_inactive() -> None:
    entity, _ = ApiKey.generate(client_name="propflow", scopes=[])
    entity.active = False
    assert entity.is_valid() is False


def test_is_valid_returns_false_when_expired() -> None:
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    entity, _ = ApiKey.generate(client_name="propflow", scopes=[], expires_at=past)
    assert entity.is_valid() is False


def test_is_valid_returns_true_when_active_and_no_expiry() -> None:
    entity, _ = ApiKey.generate(client_name="propflow", scopes=[])
    assert entity.is_valid() is True


def test_is_valid_returns_true_when_active_and_future_expiry() -> None:
    future = datetime.now(timezone.utc) + timedelta(days=365)
    entity, _ = ApiKey.generate(client_name="propflow", scopes=[], expires_at=future)
    assert entity.is_valid() is True


def test_revoke_sets_active_false() -> None:
    entity, _ = ApiKey.generate(client_name="propflow", scopes=[])
    assert entity.active is True
    entity.revoke()
    assert entity.active is False

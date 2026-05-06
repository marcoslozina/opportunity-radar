from __future__ import annotations

import time

import pytest

from core.circuit_breaker import CircuitBreaker, State


class TestCircuitBreakerInitialState:
    def test_initial_state_is_closed(self) -> None:
        cb = CircuitBreaker()
        assert cb.state == State.CLOSED
        assert not cb.is_open()


class TestCircuitBreakerOpens:
    def test_opens_after_failure_threshold(self) -> None:
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(5):
            cb.record_failure()
        assert cb.state == State.OPEN
        assert cb.is_open()

    def test_does_not_open_before_threshold(self) -> None:
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(4):
            cb.record_failure()
        assert cb.state == State.CLOSED
        assert not cb.is_open()

    def test_record_success_resets_to_closed(self) -> None:
        cb = CircuitBreaker(failure_threshold=5)
        for _ in range(5):
            cb.record_failure()
        assert cb.is_open()
        cb.record_success()
        assert cb.state == State.CLOSED
        assert not cb.is_open()


class TestCircuitBreakerHalfOpen:
    def test_transitions_to_half_open_after_recovery_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
        for _ in range(5):
            cb.record_failure()
        assert cb.state == State.OPEN

        # Simulate time passing beyond recovery_timeout
        future = time.monotonic() + 31.0
        monkeypatch.setattr("core.circuit_breaker.time.monotonic", lambda: future)

        assert cb.state == State.HALF_OPEN
        assert not cb.is_open()

    def test_stays_open_before_recovery_timeout(self, monkeypatch: pytest.MonkeyPatch) -> None:
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)
        for _ in range(5):
            cb.record_failure()

        # Simulate time passing but NOT beyond recovery_timeout
        future = time.monotonic() + 10.0
        monkeypatch.setattr("core.circuit_breaker.time.monotonic", lambda: future)

        assert cb.state == State.OPEN
        assert cb.is_open()

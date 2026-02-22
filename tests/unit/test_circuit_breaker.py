"""Unit tests for CircuitBreaker."""

from __future__ import annotations

import time
from typing import Any

import pytest

from openclaw_sdk.core.exceptions import CircuitOpenError, OpenClawError
from openclaw_sdk.resilience.circuit_breaker import CircuitBreaker


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


async def _succeed() -> dict[str, Any]:
    return {"ok": True}


async def _fail() -> dict[str, Any]:
    raise RuntimeError("boom")


# ------------------------------------------------------------------ #
# test_starts_closed
# ------------------------------------------------------------------ #


def test_starts_closed() -> None:
    """A new CircuitBreaker should start in the closed state."""
    cb = CircuitBreaker()
    assert cb.state == "closed"


# ------------------------------------------------------------------ #
# test_opens_after_threshold_failures
# ------------------------------------------------------------------ #


async def test_opens_after_threshold_failures() -> None:
    """Circuit should open after reaching the failure threshold."""
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=9999.0)

    for _ in range(3):
        with pytest.raises(RuntimeError):
            await cb.execute(_fail)

    assert cb.state == "open"


# ------------------------------------------------------------------ #
# test_rejects_when_open
# ------------------------------------------------------------------ #


async def test_rejects_when_open() -> None:
    """An open circuit should reject calls with CircuitOpenError."""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=9999.0)

    # Trip the breaker.
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await cb.execute(_fail)

    assert cb.state == "open"

    with pytest.raises(CircuitOpenError, match="rejected"):
        await cb.execute(_succeed)


# ------------------------------------------------------------------ #
# test_half_open_after_recovery_timeout
# ------------------------------------------------------------------ #


async def test_half_open_after_recovery_timeout() -> None:
    """Circuit should transition to half_open after the recovery timeout."""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.5)

    # Trip the breaker.
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await cb.execute(_fail)

    assert cb.state == "open"

    # Simulate time passing beyond recovery_timeout.
    cb._opened_at = time.monotonic() - 1.0

    assert cb.state == "half_open"


# ------------------------------------------------------------------ #
# test_closes_on_success_in_half_open
# ------------------------------------------------------------------ #


async def test_closes_on_success_in_half_open() -> None:
    """A successful call in half_open should close the circuit."""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=9999.0)

    # Trip the breaker.
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await cb.execute(_fail)

    assert cb.state == "open"

    # Move past recovery timeout.
    cb._opened_at = time.monotonic() - 10000.0
    assert cb.state == "half_open"

    # Successful probe should close the circuit.
    result = await cb.execute(_succeed)
    assert result == {"ok": True}
    assert cb.state == "closed"


# ------------------------------------------------------------------ #
# test_reopens_on_failure_in_half_open
# ------------------------------------------------------------------ #


async def test_reopens_on_failure_in_half_open() -> None:
    """A failed call in half_open should re-open the circuit."""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=9999.0)

    # Trip the breaker.
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await cb.execute(_fail)

    assert cb.state == "open"

    # Move past recovery timeout.
    cb._opened_at = time.monotonic() - 10000.0
    assert cb.state == "half_open"

    # Failed probe should re-open the circuit.
    with pytest.raises(RuntimeError):
        await cb.execute(_fail)

    assert cb.state == "open"


# ------------------------------------------------------------------ #
# test_reset_method
# ------------------------------------------------------------------ #


async def test_reset_method() -> None:
    """reset() should return the circuit to the closed state."""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=9999.0)

    # Trip the breaker.
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await cb.execute(_fail)

    assert cb.state == "open"

    cb.reset()
    assert cb.state == "closed"

    # Should be able to execute calls again.
    result = await cb.execute(_succeed)
    assert result == {"ok": True}


# ------------------------------------------------------------------ #
# test_success_resets_failure_count
# ------------------------------------------------------------------ #


async def test_success_resets_failure_count() -> None:
    """A success in the closed state should reset the failure counter."""
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=9999.0)

    # Accumulate 2 failures (below threshold).
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await cb.execute(_fail)

    assert cb.state == "closed"

    # A success resets the counter.
    result = await cb.execute(_succeed)
    assert result == {"ok": True}

    # Need 3 more failures to trip, not 1.
    for _ in range(2):
        with pytest.raises(RuntimeError):
            await cb.execute(_fail)

    assert cb.state == "closed"  # Still closed -- only 2 consecutive failures.

    with pytest.raises(RuntimeError):
        await cb.execute(_fail)

    assert cb.state == "open"  # Now 3 consecutive failures.


# ------------------------------------------------------------------ #
# test_custom_thresholds
# ------------------------------------------------------------------ #


async def test_custom_thresholds() -> None:
    """Circuit should respect custom failure_threshold and half_open_max_calls."""
    cb = CircuitBreaker(
        failure_threshold=1,
        recovery_timeout=9999.0,
        half_open_max_calls=2,
    )

    # Single failure trips the breaker.
    with pytest.raises(RuntimeError):
        await cb.execute(_fail)

    assert cb.state == "open"

    # Move past recovery timeout.
    cb._opened_at = time.monotonic() - 10000.0
    assert cb.state == "half_open"

    # First probe -- allowed (half_open_max_calls=2).
    result = await cb.execute(_succeed)
    assert result == {"ok": True}
    # After success in half_open, circuit closes.
    assert cb.state == "closed"


# ------------------------------------------------------------------ #
# test_circuit_open_error_is_openclaw_error
# ------------------------------------------------------------------ #


def test_circuit_open_error_is_openclaw_error() -> None:
    """CircuitOpenError should be a subclass of OpenClawError."""
    assert issubclass(CircuitOpenError, OpenClawError)

    err = CircuitOpenError("test", code="CIRCUIT_OPEN")
    assert isinstance(err, OpenClawError)
    assert str(err) == "test"
    assert err.code == "CIRCUIT_OPEN"
    assert err.is_retryable is False

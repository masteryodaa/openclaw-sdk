"""Tests for retry_async decorator and RetryPolicy.as_decorator."""

from __future__ import annotations

import pytest

from openclaw_sdk.core.exceptions import GatewayError
from openclaw_sdk.resilience.retry import RetryPolicy, retry_async


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _CustomRetryableError(Exception):
    """A custom exception to use in tests."""


# ---------------------------------------------------------------------------
# retry_async decorator tests
# ---------------------------------------------------------------------------


async def test_decorator_succeeds_first_try() -> None:
    """Decorated function that succeeds immediately should just return."""

    @retry_async(max_retries=3, backoff_base=0.0)
    async def succeed() -> str:
        return "ok"

    result = await succeed()
    assert result == "ok"


async def test_decorator_retries_on_failure() -> None:
    """Decorated function should retry on retryable exceptions."""
    call_count = 0

    @retry_async(max_retries=3, backoff_base=0.0, jitter=False)
    async def flaky() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise GatewayError("transient error")
        return "recovered"

    result = await flaky()
    assert result == "recovered"
    assert call_count == 3


async def test_decorator_exhausts_retries() -> None:
    """Decorated function should raise after exhausting all retries."""
    call_count = 0

    @retry_async(max_retries=2, backoff_base=0.0, jitter=False)
    async def always_fail() -> str:
        nonlocal call_count
        call_count += 1
        raise GatewayError("persistent error")

    with pytest.raises(GatewayError, match="persistent error"):
        await always_fail()

    # 1 initial + 2 retries = 3 attempts
    assert call_count == 3


async def test_decorator_preserves_function_name() -> None:
    """Decorated function should preserve the original function's metadata."""

    @retry_async(max_retries=1, backoff_base=0.0)
    async def my_special_function() -> None:
        """My docstring."""

    assert my_special_function.__name__ == "my_special_function"
    assert my_special_function.__doc__ == "My docstring."


async def test_decorator_non_retryable_not_retried() -> None:
    """Non-retryable exceptions should be raised immediately without retry."""
    call_count = 0

    @retry_async(max_retries=5, backoff_base=0.0)
    async def fail_with_value_error() -> str:
        nonlocal call_count
        call_count += 1
        raise ValueError("not retryable")

    with pytest.raises(ValueError, match="not retryable"):
        await fail_with_value_error()

    # Should only be called once — no retries for non-retryable exception.
    assert call_count == 1


# ---------------------------------------------------------------------------
# RetryPolicy.as_decorator tests
# ---------------------------------------------------------------------------


async def test_as_decorator_method() -> None:
    """RetryPolicy.as_decorator() should work like retry_async."""
    call_count = 0
    policy = RetryPolicy(max_retries=2, backoff_base=0.0, jitter=False)

    @policy.as_decorator()
    async def flaky() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise GatewayError("transient")
        return "ok"

    result = await flaky()
    assert result == "ok"
    assert call_count == 2


async def test_retry_async_convenience() -> None:
    """retry_async should be a convenient shorthand for RetryPolicy + as_decorator."""
    call_count = 0

    @retry_async(max_retries=1, backoff_base=0.0, jitter=False)
    async def once_flaky() -> str:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise GatewayError("first try fails")
        return "second try works"

    result = await once_flaky()
    assert result == "second try works"
    assert call_count == 2


async def test_custom_retryable_exceptions() -> None:
    """retry_async should respect custom retryable_exceptions tuple."""
    call_count = 0

    @retry_async(
        max_retries=3,
        backoff_base=0.0,
        jitter=False,
        retryable_exceptions=(_CustomRetryableError,),
    )
    async def custom_flaky() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise _CustomRetryableError("custom transient")
        return "ok"

    result = await custom_flaky()
    assert result == "ok"
    assert call_count == 3

    # Now verify that GatewayError is NOT retried with this custom config.
    gateway_call_count = 0

    @retry_async(
        max_retries=3,
        backoff_base=0.0,
        jitter=False,
        retryable_exceptions=(_CustomRetryableError,),
    )
    async def fail_with_gateway() -> str:
        nonlocal gateway_call_count
        gateway_call_count += 1
        raise GatewayError("not in retryable list")

    with pytest.raises(GatewayError):
        await fail_with_gateway()

    # GatewayError is not in the custom retryable list, so no retries.
    assert gateway_call_count == 1

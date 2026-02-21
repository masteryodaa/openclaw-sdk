"""Tests for guardrails/ module."""

from __future__ import annotations

import pytest

from openclaw_sdk.core.types import ExecutionResult, TokenUsage
from openclaw_sdk.guardrails.base import Guardrail, GuardrailResult
from openclaw_sdk.guardrails.builtin import (
    ContentFilterGuardrail,
    CostLimitGuardrail,
    MaxTokensGuardrail,
    PIIGuardrail,
    RegexFilterGuardrail,
)
from openclaw_sdk.tracking.cost import CostTracker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MODEL = "claude-sonnet-4-20250514"


def _make_result(
    input_tokens: int = 1000,
    output_tokens: int = 500,
    latency_ms: int = 250,
) -> ExecutionResult:
    return ExecutionResult(
        success=True,
        content="response",
        latency_ms=latency_ms,
        token_usage=TokenUsage(input=input_tokens, output=output_tokens),
    )


# ---------------------------------------------------------------------------
# PIIGuardrail — block mode (default)
# ---------------------------------------------------------------------------


async def test_pii_blocks_email() -> None:
    g = PIIGuardrail()
    result = await g.check_input("Send to alice@example.com please")
    assert not result.passed
    assert "email" in result.message


async def test_pii_blocks_phone() -> None:
    g = PIIGuardrail()
    result = await g.check_input("Call me at (555) 123-4567")
    assert not result.passed
    assert "phone" in result.message


async def test_pii_blocks_ssn() -> None:
    g = PIIGuardrail()
    result = await g.check_input("My SSN is 123-45-6789")
    assert not result.passed
    assert "ssn" in result.message


async def test_pii_blocks_credit_card() -> None:
    g = PIIGuardrail()
    result = await g.check_input("Card: 4111 1111 1111 1111")
    assert not result.passed
    assert "credit_card" in result.message


# ---------------------------------------------------------------------------
# PIIGuardrail — redact mode
# ---------------------------------------------------------------------------


async def test_pii_redacts_email() -> None:
    g = PIIGuardrail(action="redact")
    result = await g.check_input("Send to alice@example.com please")
    assert result.passed
    assert result.modified_text is not None
    assert "alice@example.com" not in result.modified_text
    assert "[REDACTED]" in result.modified_text
    assert "Redacted" in result.message


# ---------------------------------------------------------------------------
# PIIGuardrail — warn mode
# ---------------------------------------------------------------------------


async def test_pii_warns_only() -> None:
    g = PIIGuardrail(action="warn")
    result = await g.check_input("Send to alice@example.com")
    assert result.passed
    assert result.modified_text is None
    assert "Warning" in result.message


# ---------------------------------------------------------------------------
# PIIGuardrail — clean text
# ---------------------------------------------------------------------------


async def test_pii_passes_clean_text() -> None:
    g = PIIGuardrail()
    result = await g.check_input("Hello, how are you today?")
    assert result.passed
    assert "No PII" in result.message


# ---------------------------------------------------------------------------
# PIIGuardrail — output check
# ---------------------------------------------------------------------------


async def test_pii_blocks_output_email() -> None:
    g = PIIGuardrail()
    result = await g.check_output("The email is bob@corp.org")
    assert not result.passed
    assert "email" in result.message


# ---------------------------------------------------------------------------
# PIIGuardrail — name property
# ---------------------------------------------------------------------------


async def test_pii_name() -> None:
    g = PIIGuardrail()
    assert g.name == "PIIGuardrail"


# ---------------------------------------------------------------------------
# CostLimitGuardrail
# ---------------------------------------------------------------------------


async def test_cost_limit_passes_under() -> None:
    tracker = CostTracker()
    # Record a small cost (under limit)
    tracker.record(
        _make_result(input_tokens=100, output_tokens=50),
        agent_id="a1",
        model=MODEL,
        query="hello",
    )
    g = CostLimitGuardrail(max_cost_usd=1.00, tracker=tracker)
    result = await g.check_input("another query")
    assert result.passed
    assert "Cost OK" in result.message


async def test_cost_limit_blocks_over() -> None:
    tracker = CostTracker()
    # Record large token usage to push cost over limit
    tracker.record(
        _make_result(input_tokens=10_000_000, output_tokens=5_000_000),
        agent_id="a1",
        model=MODEL,
        query="expensive",
    )
    g = CostLimitGuardrail(max_cost_usd=0.01, tracker=tracker)
    result = await g.check_input("one more")
    assert not result.passed
    assert "exceeded" in result.message


async def test_cost_limit_no_tracker() -> None:
    g = CostLimitGuardrail(max_cost_usd=1.00, tracker=None)
    result = await g.check_input("anything")
    assert result.passed
    assert "No cost tracker" in result.message


async def test_cost_limit_output_always_passes() -> None:
    tracker = CostTracker()
    tracker.record(
        _make_result(input_tokens=10_000_000, output_tokens=5_000_000),
        agent_id="a1",
        model=MODEL,
        query="expensive",
    )
    g = CostLimitGuardrail(max_cost_usd=0.01, tracker=tracker)
    result = await g.check_output("some output")
    assert result.passed


# ---------------------------------------------------------------------------
# ContentFilterGuardrail
# ---------------------------------------------------------------------------


async def test_content_filter_blocks_word() -> None:
    g = ContentFilterGuardrail(blocked_words=["badword", "spam"])
    result = await g.check_input("This contains badword here")
    assert not result.passed
    assert "badword" in result.message


async def test_content_filter_case_insensitive() -> None:
    g = ContentFilterGuardrail(blocked_words=["BadWord"], case_sensitive=False)
    result = await g.check_input("this has BADWORD in it")
    assert not result.passed
    assert "badword" in result.message


async def test_content_filter_case_sensitive() -> None:
    g = ContentFilterGuardrail(blocked_words=["BadWord"], case_sensitive=True)
    # Lowercase should not match
    result = await g.check_input("this has badword in it")
    assert result.passed

    # Exact case should match
    result2 = await g.check_input("this has BadWord in it")
    assert not result2.passed


async def test_content_filter_passes_clean() -> None:
    g = ContentFilterGuardrail(blocked_words=["spam", "phishing"])
    result = await g.check_input("This is a perfectly fine message")
    assert result.passed
    assert "No blocked" in result.message


async def test_content_filter_blocks_output() -> None:
    g = ContentFilterGuardrail(blocked_words=["forbidden"])
    result = await g.check_output("The answer is forbidden knowledge")
    assert not result.passed


# ---------------------------------------------------------------------------
# MaxTokensGuardrail
# ---------------------------------------------------------------------------


async def test_max_tokens_passes_short() -> None:
    g = MaxTokensGuardrail(max_chars=100)
    result = await g.check_output("Short response")
    assert result.passed
    assert "OK" in result.message


async def test_max_tokens_blocks_long() -> None:
    g = MaxTokensGuardrail(max_chars=10)
    result = await g.check_output("This is a very long response that exceeds the limit")
    assert not result.passed
    assert "too long" in result.message


async def test_max_tokens_input_always_passes() -> None:
    g = MaxTokensGuardrail(max_chars=5)
    result = await g.check_input("This is a long input but it should still pass")
    assert result.passed


async def test_max_tokens_exact_boundary() -> None:
    g = MaxTokensGuardrail(max_chars=5)
    # Exactly at the boundary: should pass
    result = await g.check_output("abcde")
    assert result.passed

    # One over: should fail
    result2 = await g.check_output("abcdef")
    assert not result2.passed


# ---------------------------------------------------------------------------
# RegexFilterGuardrail
# ---------------------------------------------------------------------------


async def test_regex_filter_blocks_match() -> None:
    g = RegexFilterGuardrail(patterns=[r"\bpassword\b", r"\bsecret\b"])
    result = await g.check_input("My password is 12345")
    assert not result.passed
    assert "password" in result.message


async def test_regex_filter_passes_no_match() -> None:
    g = RegexFilterGuardrail(patterns=[r"\bpassword\b", r"\bsecret\b"])
    result = await g.check_input("Hello world, how are you?")
    assert result.passed
    assert "No regex" in result.message


async def test_regex_filter_blocks_output() -> None:
    g = RegexFilterGuardrail(patterns=[r"api[_\-]?key"])
    result = await g.check_output("Here is your api_key: abc123")
    assert not result.passed


async def test_regex_filter_warn_mode() -> None:
    g = RegexFilterGuardrail(patterns=[r"\btoken\b"], action="warn")
    result = await g.check_input("Send me a token")
    assert result.passed
    assert "Warning" in result.message


async def test_regex_filter_multiple_matches() -> None:
    g = RegexFilterGuardrail(patterns=[r"\bfoo\b", r"\bbar\b"])
    result = await g.check_input("foo and bar together")
    assert not result.passed
    assert "foo" in result.message
    assert "bar" in result.message


# ---------------------------------------------------------------------------
# GuardrailResult model
# ---------------------------------------------------------------------------


async def test_guardrail_result_defaults() -> None:
    r = GuardrailResult(passed=True, guardrail_name="Test")
    assert r.passed
    assert r.guardrail_name == "Test"
    assert r.message == ""
    assert r.modified_text is None


async def test_guardrail_result_with_modified_text() -> None:
    r = GuardrailResult(
        passed=True,
        guardrail_name="Redactor",
        message="Redacted",
        modified_text="clean text",
    )
    assert r.modified_text == "clean text"


# ---------------------------------------------------------------------------
# Abstract base class contract
# ---------------------------------------------------------------------------


async def test_guardrail_is_abstract() -> None:
    """Guardrail cannot be instantiated directly."""
    with pytest.raises(TypeError):
        Guardrail()  # type: ignore[abstract]

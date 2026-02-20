"""Tests for core/exceptions.py — all exception subclasses."""
from __future__ import annotations

import pytest

from openclaw_sdk.core.exceptions import (
    AgentExecutionError,
    AgentNotFoundError,
    CallbackError,
    ChannelError,
    ConfigurationError,
    GatewayError,
    OpenClawError,
    OutputParsingError,
    PipelineError,
    ScheduleError,
    SkillError,
    SkillNotFoundError,
    StreamError,
    TimeoutError,
    WebhookError,
)
from openclaw_sdk.core.exceptions import ConnectionError as OcConnectionError


# ---------------------------------------------------------------------------
# OpenClawError — base class
# ---------------------------------------------------------------------------


def test_base_exception_message() -> None:
    exc = OpenClawError("something went wrong")
    assert str(exc) == "something went wrong"


def test_base_exception_code_default_none() -> None:
    exc = OpenClawError("msg")
    assert exc.code is None


def test_base_exception_details_default_empty_dict() -> None:
    exc = OpenClawError("msg")
    assert exc.details == {}


def test_base_exception_with_code_and_details() -> None:
    exc = OpenClawError("msg", code="ERR_001", details={"key": "value"})
    assert exc.code == "ERR_001"
    assert exc.details == {"key": "value"}


def test_base_exception_details_none_becomes_empty_dict() -> None:
    exc = OpenClawError("msg", details=None)
    assert exc.details == {}


def test_base_exception_is_exception() -> None:
    exc = OpenClawError("msg")
    assert isinstance(exc, Exception)


# ---------------------------------------------------------------------------
# Can raise and catch OpenClawError
# ---------------------------------------------------------------------------


def test_can_raise_and_catch_base() -> None:
    with pytest.raises(OpenClawError, match="base error"):
        raise OpenClawError("base error", code="BASE")


# ---------------------------------------------------------------------------
# ConfigurationError
# ---------------------------------------------------------------------------


def test_configuration_error_is_openclaw_error() -> None:
    exc = ConfigurationError("bad config")
    assert isinstance(exc, OpenClawError)
    assert isinstance(exc, ConfigurationError)


def test_configuration_error_attributes() -> None:
    exc = ConfigurationError("bad config", code="CFG_01", details={"field": "gateway_ws_url"})
    assert exc.code == "CFG_01"
    assert exc.details["field"] == "gateway_ws_url"


def test_configuration_error_can_be_raised() -> None:
    with pytest.raises(ConfigurationError):
        raise ConfigurationError("missing gateway")


# ---------------------------------------------------------------------------
# ConnectionError
# ---------------------------------------------------------------------------


def test_connection_error_is_openclaw_error() -> None:
    exc = OcConnectionError("cannot connect")
    assert isinstance(exc, OpenClawError)


def test_connection_error_default_details() -> None:
    exc = OcConnectionError("timeout")
    assert exc.details == {}


# ---------------------------------------------------------------------------
# GatewayError
# ---------------------------------------------------------------------------


def test_gateway_error_is_openclaw_error() -> None:
    exc = GatewayError("gateway failed")
    assert isinstance(exc, OpenClawError)
    assert isinstance(exc, GatewayError)


def test_gateway_error_with_http_code() -> None:
    exc = GatewayError("HTTP 500", code="500", details={"raw": "Internal Server Error"})
    assert exc.code == "500"
    assert exc.details["raw"] == "Internal Server Error"


# ---------------------------------------------------------------------------
# AgentNotFoundError
# ---------------------------------------------------------------------------


def test_agent_not_found_error_is_openclaw_error() -> None:
    exc = AgentNotFoundError("agent 'bot' not found")
    assert isinstance(exc, OpenClawError)


# ---------------------------------------------------------------------------
# AgentExecutionError
# ---------------------------------------------------------------------------


def test_agent_execution_error_is_openclaw_error() -> None:
    exc = AgentExecutionError("execution failed")
    assert isinstance(exc, OpenClawError)
    assert isinstance(exc, AgentExecutionError)


def test_agent_execution_error_can_wrap_cause() -> None:
    cause = ValueError("inner error")
    exc = AgentExecutionError("execution failed")
    try:
        raise exc from cause
    except AgentExecutionError as caught:
        assert caught.__cause__ is cause


# ---------------------------------------------------------------------------
# TimeoutError
# ---------------------------------------------------------------------------


def test_timeout_error_is_openclaw_error() -> None:
    exc = TimeoutError("timed out after 30s")
    assert isinstance(exc, OpenClawError)
    assert isinstance(exc, TimeoutError)


def test_timeout_error_not_builtin_confusion() -> None:
    # Ensure our TimeoutError is distinct (it inherits from OpenClawError)
    exc = TimeoutError("custom timeout")
    assert isinstance(exc, OpenClawError)


# ---------------------------------------------------------------------------
# StreamError
# ---------------------------------------------------------------------------


def test_stream_error_is_openclaw_error() -> None:
    exc = StreamError("stream broken")
    assert isinstance(exc, OpenClawError)


# ---------------------------------------------------------------------------
# ChannelError
# ---------------------------------------------------------------------------


def test_channel_error_is_openclaw_error() -> None:
    exc = ChannelError("channel offline")
    assert isinstance(exc, OpenClawError)


# ---------------------------------------------------------------------------
# SkillError and SkillNotFoundError (hierarchy)
# ---------------------------------------------------------------------------


def test_skill_error_is_openclaw_error() -> None:
    exc = SkillError("skill failed")
    assert isinstance(exc, OpenClawError)
    assert isinstance(exc, SkillError)


def test_skill_not_found_error_is_skill_error() -> None:
    exc = SkillNotFoundError("skill 'foo' not found")
    assert isinstance(exc, SkillError)
    assert isinstance(exc, OpenClawError)


def test_skill_not_found_can_be_caught_as_skill_error() -> None:
    with pytest.raises(SkillError):
        raise SkillNotFoundError("missing skill")


# ---------------------------------------------------------------------------
# WebhookError
# ---------------------------------------------------------------------------


def test_webhook_error_is_openclaw_error() -> None:
    exc = WebhookError("webhook delivery failed")
    assert isinstance(exc, OpenClawError)


# ---------------------------------------------------------------------------
# ScheduleError
# ---------------------------------------------------------------------------


def test_schedule_error_is_openclaw_error() -> None:
    exc = ScheduleError("cron expression invalid")
    assert isinstance(exc, OpenClawError)


# ---------------------------------------------------------------------------
# PipelineError
# ---------------------------------------------------------------------------


def test_pipeline_error_is_openclaw_error() -> None:
    exc = PipelineError("pipeline step failed")
    assert isinstance(exc, OpenClawError)


# ---------------------------------------------------------------------------
# OutputParsingError
# ---------------------------------------------------------------------------


def test_output_parsing_error_is_openclaw_error() -> None:
    exc = OutputParsingError("JSON parse failed")
    assert isinstance(exc, OpenClawError)


# ---------------------------------------------------------------------------
# CallbackError
# ---------------------------------------------------------------------------


def test_callback_error_is_openclaw_error() -> None:
    exc = CallbackError("callback raised")
    assert isinstance(exc, OpenClawError)


# ---------------------------------------------------------------------------
# Full hierarchy cross-check (isinstance)
# ---------------------------------------------------------------------------


def test_all_subclasses_are_openclaw_errors() -> None:
    subclasses = [
        ConfigurationError("x"),
        OcConnectionError("x"),
        GatewayError("x"),
        AgentNotFoundError("x"),
        AgentExecutionError("x"),
        TimeoutError("x"),
        StreamError("x"),
        ChannelError("x"),
        SkillError("x"),
        SkillNotFoundError("x"),
        WebhookError("x"),
        ScheduleError("x"),
        PipelineError("x"),
        OutputParsingError("x"),
        CallbackError("x"),
    ]
    for exc in subclasses:
        assert isinstance(exc, OpenClawError), f"{type(exc).__name__} is not an OpenClawError"
        assert isinstance(exc, Exception), f"{type(exc).__name__} is not an Exception"

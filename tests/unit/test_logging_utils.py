"""Tests for utils/logging.py — configure_logging and get_logger."""
from __future__ import annotations

import logging

import structlog

from openclaw_sdk.utils.logging import configure_logging, get_logger


# ---------------------------------------------------------------------------
# configure_logging
# ---------------------------------------------------------------------------


def test_configure_logging_info_json_does_not_raise() -> None:
    configure_logging("INFO", json=True)


def test_configure_logging_debug_text_does_not_raise() -> None:
    configure_logging("DEBUG", json=False)


def test_configure_logging_warning_json_does_not_raise() -> None:
    configure_logging("WARNING", json=True)


def test_configure_logging_error_text_does_not_raise() -> None:
    configure_logging("ERROR", json=False)


def test_configure_logging_sets_root_level_debug() -> None:
    configure_logging("DEBUG", json=False)
    root = logging.getLogger()
    assert root.level == logging.DEBUG


def test_configure_logging_sets_root_level_info() -> None:
    configure_logging("INFO", json=True)
    root = logging.getLogger()
    assert root.level == logging.INFO


def test_configure_logging_sets_root_level_warning() -> None:
    configure_logging("WARNING", json=False)
    root = logging.getLogger()
    assert root.level == logging.WARNING


def test_configure_logging_sets_handler() -> None:
    configure_logging("INFO", json=True)
    root = logging.getLogger()
    assert len(root.handlers) > 0


def test_configure_logging_default_args_do_not_raise() -> None:
    # Default: level="INFO", json=True
    configure_logging()


def test_configure_logging_invalid_level_falls_back_to_info() -> None:
    # An unknown level string should fall back gracefully (getattr returns None → INFO)
    configure_logging("NOTAREAL_LEVEL", json=False)
    root = logging.getLogger()
    # Since getattr returns None and we use 'or INFO', level should be INFO
    assert root.level == logging.INFO


# ---------------------------------------------------------------------------
# get_logger
# ---------------------------------------------------------------------------


def test_get_logger_returns_truthy() -> None:
    logger = get_logger("test.module")
    assert logger is not None


def test_get_logger_returns_bound_logger_type() -> None:
    logger = get_logger("test.logging")
    # structlog loggers are bound loggers; check they have a log method
    assert hasattr(logger, "info")
    assert hasattr(logger, "debug")
    assert hasattr(logger, "warning")
    assert hasattr(logger, "error")


def test_get_logger_different_names_return_loggers() -> None:
    logger_a = get_logger("module.a")
    logger_b = get_logger("module.b")
    assert logger_a is not None
    assert logger_b is not None


def test_get_logger_can_log_without_raising() -> None:
    configure_logging("WARNING", json=False)
    logger = get_logger("test.noop")
    # Should not raise even if nothing is listening
    logger.info("test message", key="value")


def test_get_logger_with_sdk_name() -> None:
    logger = get_logger("openclaw_sdk.core.client")
    assert logger is not None

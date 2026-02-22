"""Tests for ClientConfig.from_env() and env-based connect()."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.gateway.mock import MockGateway


# ---------------------------------------------------------------------------
# from_env() tests
# ---------------------------------------------------------------------------


def test_from_env_reads_gateway_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENCLAW_GATEWAY_URL", "ws://custom:9999/gateway")
    config = ClientConfig.from_env()
    assert config.gateway_ws_url == "ws://custom:9999/gateway"


def test_from_env_reads_gateway_ws_url_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """OPENCLAW_GATEWAY_WS_URL is used when OPENCLAW_GATEWAY_URL is not set."""
    monkeypatch.delenv("OPENCLAW_GATEWAY_URL", raising=False)
    monkeypatch.setenv("OPENCLAW_GATEWAY_WS_URL", "ws://fallback:1234/gw")
    config = ClientConfig.from_env()
    assert config.gateway_ws_url == "ws://fallback:1234/gw"


def test_from_env_gateway_url_takes_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    """OPENCLAW_GATEWAY_URL takes priority over OPENCLAW_GATEWAY_WS_URL."""
    monkeypatch.setenv("OPENCLAW_GATEWAY_URL", "ws://primary:1111/gw")
    monkeypatch.setenv("OPENCLAW_GATEWAY_WS_URL", "ws://secondary:2222/gw")
    config = ClientConfig.from_env()
    assert config.gateway_ws_url == "ws://primary:1111/gw"


def test_from_env_reads_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENCLAW_API_KEY", "sk-test-key-123")
    config = ClientConfig.from_env()
    assert config.api_key == "sk-test-key-123"


def test_from_env_defaults_when_not_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """All values fall back to ClientConfig defaults when env vars are absent."""
    monkeypatch.delenv("OPENCLAW_GATEWAY_URL", raising=False)
    monkeypatch.delenv("OPENCLAW_GATEWAY_WS_URL", raising=False)
    monkeypatch.delenv("OPENCLAW_API_KEY", raising=False)
    monkeypatch.delenv("OPENCLAW_MODE", raising=False)
    monkeypatch.delenv("OPENCLAW_TIMEOUT", raising=False)
    monkeypatch.delenv("OPENCLAW_LOG_LEVEL", raising=False)

    config = ClientConfig.from_env()
    assert config.gateway_ws_url is None
    assert config.api_key is None
    assert config.mode == "auto"
    assert config.timeout == 300
    assert config.log_level == "INFO"


def test_from_env_reads_timeout_as_int(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENCLAW_TIMEOUT", "60")
    config = ClientConfig.from_env()
    assert config.timeout == 60
    assert isinstance(config.timeout, int)


def test_from_env_reads_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENCLAW_MODE", "protocol")
    config = ClientConfig.from_env()
    assert config.mode == "protocol"


def test_from_env_reads_log_level(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENCLAW_LOG_LEVEL", "DEBUG")
    config = ClientConfig.from_env()
    assert config.log_level == "DEBUG"


# ---------------------------------------------------------------------------
# connect() uses env vars when no config kwargs are passed
# ---------------------------------------------------------------------------


async def test_connect_uses_env_when_no_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """OpenClawClient.connect() reads OPENCLAW_* env vars when no kwargs are given."""
    monkeypatch.setenv("OPENCLAW_GATEWAY_URL", "ws://env-host:8888/gateway")
    monkeypatch.setenv("OPENCLAW_API_KEY", "env-key-456")

    mock_gw = MockGateway()

    with patch.object(OpenClawClient, "_build_gateway", return_value=mock_gw):
        client = await OpenClawClient.connect()

    assert client.config.gateway_ws_url == "ws://env-host:8888/gateway"
    assert client.config.api_key == "env-key-456"


async def test_connect_prefers_explicit_kwargs_over_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When kwargs are passed, env vars are NOT consulted."""
    monkeypatch.setenv("OPENCLAW_GATEWAY_URL", "ws://env-host:8888/gateway")

    mock_gw = MockGateway()

    with patch.object(OpenClawClient, "_build_gateway", return_value=mock_gw):
        client = await OpenClawClient.connect(gateway_ws_url="ws://explicit:1234/gw")

    assert client.config.gateway_ws_url == "ws://explicit:1234/gw"

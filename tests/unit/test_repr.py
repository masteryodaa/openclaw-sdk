"""Tests for __repr__ on Agent, OpenClawClient, and Pipeline."""
from __future__ import annotations

from openclaw_sdk.core.agent import Agent
from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.gateway.mock import MockGateway
from openclaw_sdk.pipeline.pipeline import Pipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(*, connected: bool = True) -> OpenClawClient:
    mock = MockGateway()
    mock._connected = connected
    return OpenClawClient(config=ClientConfig(), gateway=mock)


# ---------------------------------------------------------------------------
# Agent.__repr__
# ---------------------------------------------------------------------------


def test_agent_repr() -> None:
    client = _make_client()
    agent = Agent(client, "bot", "main")
    assert repr(agent) == "Agent(agent_id='bot', session='main')"


def test_agent_repr_custom_session() -> None:
    client = _make_client()
    agent = Agent(client, "research-bot", "weekly")
    assert repr(agent) == "Agent(agent_id='research-bot', session='weekly')"


# ---------------------------------------------------------------------------
# OpenClawClient.__repr__
# ---------------------------------------------------------------------------


def test_client_repr() -> None:
    client = _make_client(connected=True)
    assert repr(client) == "OpenClawClient(mode='auto', connected=True)"


def test_client_repr_disconnected() -> None:
    client = _make_client(connected=False)
    assert repr(client) == "OpenClawClient(mode='auto', connected=False)"


def test_client_repr_custom_mode() -> None:
    mock = MockGateway()
    mock._connected = True
    client = OpenClawClient(
        config=ClientConfig(mode="protocol"),
        gateway=mock,
    )
    assert repr(client) == "OpenClawClient(mode='protocol', connected=True)"


# ---------------------------------------------------------------------------
# Pipeline.__repr__
# ---------------------------------------------------------------------------


def test_pipeline_repr() -> None:
    client = _make_client()
    pipe = Pipeline(client)
    assert repr(pipe) == "Pipeline(steps=0)"


def test_pipeline_repr_with_steps() -> None:
    client = _make_client()
    pipe = Pipeline(client)
    pipe.add_step("step1", "agent1", "prompt1")
    pipe.add_step("step2", "agent2", "prompt2")
    pipe.add_step("step3", "agent3", "prompt3")
    assert repr(pipe) == "Pipeline(steps=3)"

"""Tests for templates/registry.py and client.create_agent_from_template."""

from __future__ import annotations

import pytest

from openclaw_sdk.core.config import AgentConfig
from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.gateway.mock import MockGateway
from openclaw_sdk.templates.registry import get_template, list_templates, TEMPLATES
from openclaw_sdk.tools.policy import ToolPolicy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(mock: MockGateway) -> OpenClawClient:
    return OpenClawClient(config=ClientConfig(), gateway=mock)


def _register_config_methods(mock: MockGateway) -> None:
    """Register mock responses for agents.create (used by create_agent)."""
    mock.register(
        "agents.create",
        lambda p: {
            "id": p["name"] if p else "agent",
            "name": p.get("name", "agent") if p else "agent",
        },
    )


# ---------------------------------------------------------------------------
# get_template
# ---------------------------------------------------------------------------


def test_get_template_returns_agent_config() -> None:
    config = get_template("assistant")
    assert isinstance(config, AgentConfig)
    assert config.agent_id == "assistant"
    assert "helpful AI assistant" in config.system_prompt
    assert config.tool_policy is not None
    assert config.tool_policy.profile == "coding"


def test_get_template_unknown_raises() -> None:
    with pytest.raises(KeyError, match="Unknown template 'nonexistent'"):
        get_template("nonexistent")


def test_get_template_unknown_lists_available() -> None:
    with pytest.raises(KeyError, match="assistant"):
        get_template("nonexistent")


def test_get_template_customer_support_has_channels() -> None:
    config = get_template("customer-support")
    assert config.agent_id == "customer-support"
    assert "whatsapp" in config.channels
    assert "telegram" in config.channels
    assert config.tool_policy is not None
    assert config.tool_policy.profile == "minimal"


def test_get_template_devops_has_confirm_permission() -> None:
    config = get_template("devops")
    assert config.permission_mode == "confirm"
    assert config.tool_policy is not None
    assert config.tool_policy.profile == "full"


def test_get_template_mobile_jarvis_has_memory_and_confirm() -> None:
    config = get_template("mobile-jarvis")
    assert config.permission_mode == "confirm"
    assert config.enable_memory is True
    assert config.tool_policy is not None
    assert config.tool_policy.profile == "full"


# ---------------------------------------------------------------------------
# list_templates
# ---------------------------------------------------------------------------


def test_list_templates_returns_sorted() -> None:
    names = list_templates()
    assert isinstance(names, list)
    assert names == sorted(names)
    assert len(names) == len(TEMPLATES)


def test_list_templates_contains_known_names() -> None:
    names = list_templates()
    assert "assistant" in names
    assert "customer-support" in names
    assert "data-analyst" in names
    assert "code-reviewer" in names
    assert "researcher" in names
    assert "writer" in names
    assert "devops" in names
    assert "mobile-jarvis" in names


# ---------------------------------------------------------------------------
# All templates validity
# ---------------------------------------------------------------------------


def test_all_templates_valid() -> None:
    """Every template in TEMPLATES must produce a valid AgentConfig."""
    for name in TEMPLATES:
        config = get_template(name)
        assert isinstance(
            config, AgentConfig
        ), f"Template '{name}' did not produce AgentConfig"
        assert (
            config.agent_id == name
        ), f"Template '{name}' has wrong agent_id: {config.agent_id}"
        assert (
            len(config.system_prompt) > 0
        ), f"Template '{name}' has empty system_prompt"


def test_all_templates_have_tool_policy() -> None:
    """Every template should define a tool_policy."""
    for name in TEMPLATES:
        config = get_template(name)
        assert config.tool_policy is not None, f"Template '{name}' missing tool_policy"
        assert isinstance(config.tool_policy, ToolPolicy)


# ---------------------------------------------------------------------------
# create_agent_from_template (client integration)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_agent_from_template() -> None:
    mock = MockGateway()
    _register_config_methods(mock)
    await mock.connect()
    client = _make_client(mock)

    agent = await client.create_agent_from_template("assistant")
    assert agent.agent_id == "assistant"
    mock.assert_called("agents.create")
    await mock.close()


@pytest.mark.asyncio
async def test_template_override_agent_id() -> None:
    mock = MockGateway()
    _register_config_methods(mock)
    await mock.connect()
    client = _make_client(mock)

    agent = await client.create_agent_from_template(
        "assistant", agent_id="my-custom-bot"
    )
    assert agent.agent_id == "my-custom-bot"
    await mock.close()


@pytest.mark.asyncio
async def test_template_override_system_prompt() -> None:
    mock = MockGateway()
    _register_config_methods(mock)
    await mock.connect()
    client = _make_client(mock)

    agent = await client.create_agent_from_template(
        "writer",
        agent_id="blog-writer",
        system_prompt="Write blog posts about Python.",
    )
    assert agent.agent_id == "blog-writer"
    await mock.close()


@pytest.mark.asyncio
async def test_create_agent_from_template_unknown_raises() -> None:
    mock = MockGateway()
    _register_config_methods(mock)
    await mock.connect()
    client = _make_client(mock)

    with pytest.raises(KeyError, match="Unknown template"):
        await client.create_agent_from_template("nonexistent-template")
    await mock.close()


@pytest.mark.asyncio
async def test_create_agent_from_template_customer_support() -> None:
    mock = MockGateway()
    _register_config_methods(mock)
    await mock.connect()
    client = _make_client(mock)

    agent = await client.create_agent_from_template("customer-support")
    assert agent.agent_id == "customer-support"
    # Verify that agents.create was called (agent was actually created)
    assert mock.call_count("agents.create") == 1
    await mock.close()

"""Tests for SkillsConfig, SkillEntry, and related models."""

from __future__ import annotations

import json
from typing import Any

from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import AgentConfig, ClientConfig
from openclaw_sdk.gateway.mock import MockGateway
from openclaw_sdk.skills.config import (
    SkillEntry,
    SkillInstallConfig,
    SkillLoadConfig,
    SkillsConfig,
)

# ------------------------------------------------------------------ #
# SkillLoadConfig
# ------------------------------------------------------------------ #


class TestSkillLoadConfig:
    def test_defaults(self) -> None:
        cfg = SkillLoadConfig()
        assert cfg.watch is True
        assert cfg.watch_debounce_ms == 250
        assert cfg.extra_dirs == []

    def test_to_openclaw_defaults(self) -> None:
        cfg = SkillLoadConfig()
        result = cfg.to_openclaw()
        assert result["watch"] is True
        # debounce is default, omitted
        assert "watchDebounceMs" not in result
        assert "extraDirs" not in result

    def test_to_openclaw_with_extra_dirs(self) -> None:
        cfg = SkillLoadConfig(extra_dirs=["~/my-skills", "/opt/skills"])
        result = cfg.to_openclaw()
        assert result["extraDirs"] == ["~/my-skills", "/opt/skills"]

    def test_to_openclaw_with_custom_debounce(self) -> None:
        cfg = SkillLoadConfig(watch_debounce_ms=500)
        result = cfg.to_openclaw()
        assert result["watchDebounceMs"] == 500


# ------------------------------------------------------------------ #
# SkillInstallConfig
# ------------------------------------------------------------------ #


class TestSkillInstallConfig:
    def test_defaults(self) -> None:
        cfg = SkillInstallConfig()
        assert cfg.prefer_brew is False
        assert cfg.node_manager == "npm"

    def test_to_openclaw_defaults_empty(self) -> None:
        cfg = SkillInstallConfig()
        result = cfg.to_openclaw()
        assert result == {}

    def test_to_openclaw_prefer_brew(self) -> None:
        cfg = SkillInstallConfig(prefer_brew=True)
        result = cfg.to_openclaw()
        assert result["preferBrew"] is True

    def test_to_openclaw_custom_node_manager(self) -> None:
        cfg = SkillInstallConfig(node_manager="bun")
        result = cfg.to_openclaw()
        assert result["nodeManager"] == "bun"


# ------------------------------------------------------------------ #
# SkillEntry
# ------------------------------------------------------------------ #


class TestSkillEntry:
    def test_defaults(self) -> None:
        entry = SkillEntry()
        assert entry.enabled is True
        assert entry.api_key is None
        assert entry.env == {}

    def test_to_openclaw_enabled_default_empty(self) -> None:
        entry = SkillEntry()
        result = entry.to_openclaw()
        assert result == {}

    def test_to_openclaw_disabled(self) -> None:
        entry = SkillEntry(enabled=False)
        result = entry.to_openclaw()
        assert result["enabled"] is False

    def test_to_openclaw_with_api_key(self) -> None:
        entry = SkillEntry(api_key="sk-xxx")
        result = entry.to_openclaw()
        assert result["apiKey"] == "sk-xxx"

    def test_to_openclaw_with_env(self) -> None:
        entry = SkillEntry(env={"DATABASE_URL": "postgres://..."})
        result = entry.to_openclaw()
        assert result["env"]["DATABASE_URL"] == "postgres://..."


# ------------------------------------------------------------------ #
# SkillsConfig
# ------------------------------------------------------------------ #


class TestSkillsConfig:
    def test_defaults_empty(self) -> None:
        cfg = SkillsConfig()
        assert cfg.allow_bundled is None
        assert cfg.load is None
        assert cfg.install is None
        assert cfg.entries is None

    def test_to_openclaw_empty(self) -> None:
        cfg = SkillsConfig()
        result = cfg.to_openclaw()
        assert result == {}

    def test_to_openclaw_allow_bundled(self) -> None:
        cfg = SkillsConfig(allow_bundled=["clawhub", "gemini"])
        result = cfg.to_openclaw()
        assert result["allowBundled"] == ["clawhub", "gemini"]

    def test_to_openclaw_with_load(self) -> None:
        cfg = SkillsConfig(load=SkillLoadConfig(extra_dirs=["~/skills"]))
        result = cfg.to_openclaw()
        assert "extraDirs" in result["load"]

    def test_to_openclaw_with_entries(self) -> None:
        cfg = SkillsConfig(
            entries={
                "my-skill": SkillEntry(api_key="key123"),
                "disabled": SkillEntry(enabled=False),
            }
        )
        result = cfg.to_openclaw()
        assert result["entries"]["my-skill"]["apiKey"] == "key123"
        assert result["entries"]["disabled"]["enabled"] is False

    def test_to_openclaw_install_empty_omitted(self) -> None:
        cfg = SkillsConfig(install=SkillInstallConfig())
        result = cfg.to_openclaw()
        # Default install config produces empty dict, so "install" is omitted
        assert "install" not in result

    def test_to_openclaw_install_with_values(self) -> None:
        cfg = SkillsConfig(install=SkillInstallConfig(prefer_brew=True))
        result = cfg.to_openclaw()
        assert result["install"]["preferBrew"] is True


# ------------------------------------------------------------------ #
# Fluent builders
# ------------------------------------------------------------------ #


class TestSkillsConfigFluent:
    def test_with_clawhub_adds_to_allow_bundled(self) -> None:
        cfg = SkillsConfig().with_clawhub()
        assert cfg.allow_bundled is not None
        assert "clawhub" in cfg.allow_bundled

    def test_with_clawhub_does_not_duplicate(self) -> None:
        cfg = SkillsConfig(allow_bundled=["clawhub"]).with_clawhub()
        assert cfg.allow_bundled is not None
        assert cfg.allow_bundled.count("clawhub") == 1

    def test_with_clawhub_disabled_removes(self) -> None:
        cfg = SkillsConfig(allow_bundled=["clawhub", "gemini"]).with_clawhub(
            enabled=False
        )
        assert cfg.allow_bundled is not None
        assert "clawhub" not in cfg.allow_bundled
        assert "gemini" in cfg.allow_bundled

    def test_with_clawhub_returns_new_instance(self) -> None:
        original = SkillsConfig()
        modified = original.with_clawhub()
        assert original is not modified
        assert original.allow_bundled is None

    def test_with_entry(self) -> None:
        cfg = SkillsConfig().with_entry("scraper", SkillEntry(api_key="key"))
        assert cfg.entries is not None
        assert "scraper" in cfg.entries
        assert cfg.entries["scraper"].api_key == "key"

    def test_with_load(self) -> None:
        cfg = SkillsConfig().with_load(watch=False, extra_dirs=["/opt/skills"])
        assert cfg.load is not None
        assert cfg.load.watch is False
        assert cfg.load.extra_dirs == ["/opt/skills"]


# ------------------------------------------------------------------ #
# AgentConfig integration
# ------------------------------------------------------------------ #


class TestAgentConfigSkills:
    def test_to_openclaw_agent_includes_skills(self) -> None:
        cfg = AgentConfig(
            agent_id="test",
            skills=SkillsConfig(allow_bundled=["clawhub"]),
        )
        result = cfg.to_openclaw_agent()
        assert "skills" in result
        assert result["skills"]["allowBundled"] == ["clawhub"]

    def test_to_openclaw_agent_omits_empty_skills(self) -> None:
        cfg = AgentConfig(
            agent_id="test",
            skills=SkillsConfig(),
        )
        result = cfg.to_openclaw_agent()
        # Empty SkillsConfig → empty dict → omitted
        assert "skills" not in result

    def test_to_openclaw_agent_no_skills_field(self) -> None:
        cfg = AgentConfig(agent_id="test")
        result = cfg.to_openclaw_agent()
        assert "skills" not in result


# ------------------------------------------------------------------ #
# Agent runtime skill methods
# ------------------------------------------------------------------ #


def _make_config_get_response(
    agents: dict[str, Any] | None = None,
    *,
    base_hash: str | None = "abc123",
) -> dict[str, Any]:
    raw = json.dumps({"agents": agents or {}})
    result: dict[str, Any] = {"raw": raw, "exists": True, "path": "/mock"}
    if base_hash is not None:
        result["hash"] = base_hash
    return result


def _last_call_parsed(mock: MockGateway, method: str) -> dict[str, Any]:
    for m, p in reversed(mock.calls):
        if m == method:
            assert p is not None
            return json.loads(p["raw"])
    raise AssertionError(f"No call to '{method}'")


async def _setup(
    agents: dict[str, Any] | None = None,
) -> tuple[OpenClawClient, MockGateway]:
    mock = MockGateway()
    await mock.connect()
    mock.register("config.get", _make_config_get_response(agents))
    mock.register("config.patch", {"ok": True})
    client = OpenClawClient(config=ClientConfig(), gateway=mock)
    return client, mock


class TestAgentSetSkills:
    async def test_set_skills_patches_config(self) -> None:
        client, mock = await _setup()
        agent = client.get_agent("test-agent")

        await agent.set_skills(SkillsConfig(allow_bundled=["clawhub"]))

        parsed = _last_call_parsed(mock, "config.patch")
        skills = parsed["agents"]["test-agent"]["skills"]
        assert skills["allowBundled"] == ["clawhub"]


class TestAgentConfigureSkill:
    async def test_adds_skill_entry(self) -> None:
        client, mock = await _setup()
        agent = client.get_agent("test-agent")

        await agent.configure_skill("scraper", SkillEntry(api_key="sk-123"))

        parsed = _last_call_parsed(mock, "config.patch")
        entries = parsed["agents"]["test-agent"]["skills"]["entries"]
        assert entries["scraper"]["apiKey"] == "sk-123"

    async def test_preserves_existing_entries(self) -> None:
        existing = {
            "test-agent": {
                "skills": {
                    "entries": {"old-skill": {"enabled": True}},
                },
            },
        }
        client, mock = await _setup(agents=existing)
        agent = client.get_agent("test-agent")

        await agent.configure_skill("new-skill", SkillEntry(env={"KEY": "val"}))

        parsed = _last_call_parsed(mock, "config.patch")
        entries = parsed["agents"]["test-agent"]["skills"]["entries"]
        assert "old-skill" in entries
        assert "new-skill" in entries


class TestAgentDisableEnableSkill:
    async def test_disable_skill(self) -> None:
        client, mock = await _setup()
        agent = client.get_agent("test-agent")

        await agent.disable_skill("dangerous-skill")

        parsed = _last_call_parsed(mock, "config.patch")
        entries = parsed["agents"]["test-agent"]["skills"]["entries"]
        assert entries["dangerous-skill"]["enabled"] is False

    async def test_enable_skill(self) -> None:
        existing = {
            "test-agent": {
                "skills": {
                    "entries": {"my-skill": {"enabled": False}},
                },
            },
        }
        client, mock = await _setup(agents=existing)
        agent = client.get_agent("test-agent")

        await agent.enable_skill("my-skill")

        parsed = _last_call_parsed(mock, "config.patch")
        entries = parsed["agents"]["test-agent"]["skills"]["entries"]
        assert entries["my-skill"]["enabled"] is True


# ------------------------------------------------------------------ #
# create_agent with skills
# ------------------------------------------------------------------ #


class TestCreateAgentWithSkills:
    async def test_create_agent_with_skills_config(self) -> None:
        client, mock = await _setup()
        mock.register("agents.create", {"id": "skill-agent"})

        cfg = AgentConfig(
            agent_id="skill-agent",
            name="Skill Agent",
            skills=SkillsConfig(
                allow_bundled=["clawhub", "gemini"],
                entries={"web-scraper": SkillEntry(api_key="key")},
            ),
        )
        agent = await client.create_agent(cfg)

        assert agent.agent_id == "skill-agent"
        mock.assert_called("agents.create")

"""Skills configuration models mapping to OpenClaw's ``skills`` config section.

OpenClaw agents can dynamically discover and install skills from ClawHub
at runtime. This module provides typed configuration for controlling that
behavior — which skills are allowed, how they load, and per-skill settings.

Example::

    from openclaw_sdk import AgentConfig, ToolPolicy
    from openclaw_sdk.skills.config import SkillsConfig, SkillEntry

    agent = AgentConfig(
        agent_id="researcher",
        system_prompt="You are a research assistant.",
        tool_policy=ToolPolicy.coding(),
        skills=SkillsConfig(
            allow_bundled=["clawhub", "gemini", "peekaboo"],
            load=SkillLoadConfig(watch=True, extra_dirs=["~/my-skills"]),
            entries={
                "web-scraper": SkillEntry(enabled=True, env={"API_KEY": "..."}),
            },
        ),
    )
"""

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, Field


class SkillLoadConfig(BaseModel):
    """Controls how OpenClaw discovers and loads skills from the filesystem.

    Attributes:
        extra_dirs: Additional directories to scan for SKILL.md files.
            Added with lowest precedence after workspace and managed dirs.
        watch: Enable filesystem watcher for hot-reload of skill changes.
        watch_debounce_ms: Debounce interval for the watcher (ms).
    """

    extra_dirs: list[str] = Field(default_factory=list)
    watch: bool = True
    watch_debounce_ms: int = Field(default=250, ge=50, le=5000)

    def to_openclaw(self) -> dict[str, Any]:
        """Serialize to OpenClaw's camelCase JSON format."""
        result: dict[str, Any] = {}
        if self.extra_dirs:
            result["extraDirs"] = self.extra_dirs
        result["watch"] = self.watch
        if self.watch_debounce_ms != 250:
            result["watchDebounceMs"] = self.watch_debounce_ms
        return result


class SkillInstallConfig(BaseModel):
    """Controls how skills are installed when fetched from ClawHub.

    Attributes:
        prefer_brew: Prefer Homebrew installers on macOS when available.
        node_manager: Node.js package manager for skills requiring npm deps.
    """

    prefer_brew: bool = False
    node_manager: Literal["npm", "pnpm", "yarn", "bun"] = "npm"

    def to_openclaw(self) -> dict[str, Any]:
        """Serialize to OpenClaw's camelCase JSON format."""
        result: dict[str, Any] = {}
        if self.prefer_brew:
            result["preferBrew"] = True
        if self.node_manager != "npm":
            result["nodeManager"] = self.node_manager
        return result


class SkillEntry(BaseModel):
    """Per-skill configuration override.

    Attributes:
        enabled: Set to False to disable this skill.
        api_key: Convenience field for the skill's primary API credential.
        env: Environment variables injected for this skill's execution.
    """

    enabled: bool = True
    api_key: str | None = None
    env: dict[str, str] = Field(default_factory=dict)

    def to_openclaw(self) -> dict[str, Any]:
        """Serialize to OpenClaw's camelCase JSON format."""
        result: dict[str, Any] = {}
        if not self.enabled:
            result["enabled"] = False
        if self.api_key is not None:
            result["apiKey"] = self.api_key
        if self.env:
            result["env"] = self.env
        return result


class SkillsConfig(BaseModel):
    """Top-level skills configuration for an OpenClaw agent.

    Maps to the ``skills`` section of ``openclaw.json``. Controls which
    bundled skills are available, how skills are loaded from disk, install
    preferences, and per-skill overrides.

    OpenClaw's dynamic tool discovery works through the ClawHub bundled skill:
    when enabled, the agent can search ClawHub for skills it needs, install
    them, and use them on the next turn — all autonomously.

    Example::

        # Allow dynamic discovery (ClawHub is a bundled skill)
        skills = SkillsConfig(
            allow_bundled=["clawhub", "gemini"],
            entries={"my-custom-skill": SkillEntry(api_key="sk-xxx")},
        )

        # Lock down to specific skills only
        skills = SkillsConfig(
            allow_bundled=["gemini"],  # No ClawHub = no auto-discovery
        )

    Attributes:
        allow_bundled: Whitelist of bundled skill names to make available.
            If not set, all bundled skills are available (including ClawHub).
        load: Filesystem loading configuration (watch mode, extra dirs).
        install: Package manager preferences for skill installation.
        entries: Per-skill configuration overrides keyed by skill name.
    """

    allow_bundled: list[str] | None = None
    load: SkillLoadConfig | None = None
    install: SkillInstallConfig | None = None
    entries: dict[str, SkillEntry] | None = None

    def to_openclaw(self) -> dict[str, Any]:
        """Serialize to OpenClaw's camelCase JSON format."""
        result: dict[str, Any] = {}
        if self.allow_bundled is not None:
            result["allowBundled"] = self.allow_bundled
        if self.load is not None:
            result["load"] = self.load.to_openclaw()
        if self.install is not None:
            install_data = self.install.to_openclaw()
            if install_data:
                result["install"] = install_data
        if self.entries:
            result["entries"] = {
                name: entry.to_openclaw()
                for name, entry in self.entries.items()
            }
        return result

    # Fluent builders

    def with_clawhub(self, *, enabled: bool = True) -> Self:
        """Enable or disable ClawHub dynamic skill discovery.

        When ClawHub is in ``allow_bundled``, the agent can autonomously
        search for and install skills from the ClawHub marketplace.

        Args:
            enabled: If True, ensure "clawhub" is in allow_bundled.
                If False, remove it (disabling dynamic discovery).
        """
        current = list(self.allow_bundled or [])
        if enabled and "clawhub" not in current:
            current.append("clawhub")
        elif not enabled:
            current = [s for s in current if s != "clawhub"]
        return self.model_copy(update={"allow_bundled": current or None})

    def with_entry(self, name: str, entry: SkillEntry) -> Self:
        """Add or update a per-skill configuration entry."""
        current = dict(self.entries or {})
        current[name] = entry
        return self.model_copy(update={"entries": current})

    def with_load(self, **kwargs: Any) -> Self:
        """Set load configuration (watch, extra_dirs, etc.)."""
        load = SkillLoadConfig(**kwargs)
        return self.model_copy(update={"load": load})

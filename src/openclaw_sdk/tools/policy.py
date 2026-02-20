from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, Field


class ExecPolicy(BaseModel):
    """Execution policy for shell/command tools."""

    security: Literal["deny", "allowlist", "full"] = "allowlist"
    ask: Literal["off", "on-miss", "always"] = "on-miss"


class FsPolicy(BaseModel):
    """Filesystem access policy."""

    workspace_only: bool = True


class ElevatedPolicy(BaseModel):
    """Policy for elevated (sudo/admin) operations."""

    enabled: bool = False
    allow_from: list[str] = Field(default_factory=list)


class WebSearchPolicy(BaseModel):
    """Web search provider configuration."""

    provider: Literal["brave", "google", "bing", "duckduckgo"] = "brave"


class WebFetchPolicy(BaseModel):
    """Web fetch (URL retrieval) policy."""

    enabled: bool = True


class WebPolicy(BaseModel):
    """Combined web access policy."""

    search: WebSearchPolicy = Field(default_factory=WebSearchPolicy)
    fetch: WebFetchPolicy = Field(default_factory=WebFetchPolicy)


class ToolPolicy(BaseModel):
    """Maps to OpenClaw's native ``tools`` config section.

    Provides preset factories and a fluent builder API for constructing
    tool policies without touching raw JSON.

    Usage::

        policy = ToolPolicy.coding().deny("shell", "sudo").with_fs(workspace_only=True)
        payload = policy.to_openclaw()
    """

    model_config = {"populate_by_name": True}

    profile: Literal["minimal", "coding", "messaging", "full"] = "coding"
    allow: list[str] = Field(default_factory=list)
    deny_list: list[str] = Field(default_factory=list, alias="deny")
    also_allow: list[str] = Field(default_factory=list)
    exec_policy: ExecPolicy = Field(default_factory=ExecPolicy, alias="exec")
    fs: FsPolicy = Field(default_factory=FsPolicy)
    elevated: ElevatedPolicy = Field(default_factory=ElevatedPolicy)
    web: WebPolicy = Field(default_factory=WebPolicy)

    # ------------------------------------------------------------------
    # Preset factories
    # ------------------------------------------------------------------

    @classmethod
    def minimal(cls) -> Self:
        """Preset: minimal tool access."""
        return cls(profile="minimal")

    @classmethod
    def coding(cls) -> Self:
        """Preset: standard coding tools."""
        return cls(profile="coding")

    @classmethod
    def messaging(cls) -> Self:
        """Preset: messaging/channel tools."""
        return cls(profile="messaging")

    @classmethod
    def full(cls) -> Self:
        """Preset: all tools enabled."""
        return cls(profile="full")

    # ------------------------------------------------------------------
    # Fluent builder methods (return new copies — originals are immutable)
    # ------------------------------------------------------------------

    def deny(self, *tools: str) -> Self:
        """Add tools to the deny list (additive, deduplicates)."""
        merged = list(dict.fromkeys([*self.deny_list, *tools]))
        return self.model_copy(update={"deny_list": merged})

    def allow_tools(self, *tools: str) -> Self:
        """Add tools to the allow list."""
        merged = list(dict.fromkeys([*self.allow, *tools]))
        return self.model_copy(update={"allow": merged})

    def with_exec(
        self,
        security: Literal["deny", "allowlist", "full"] = "allowlist",
        ask: Literal["off", "on-miss", "always"] = "on-miss",
    ) -> Self:
        """Return a copy with updated execution policy."""
        return self.model_copy(
            update={"exec_policy": ExecPolicy(security=security, ask=ask)}
        )

    def with_fs(self, *, workspace_only: bool = True) -> Self:
        """Return a copy with updated filesystem policy."""
        return self.model_copy(
            update={"fs": FsPolicy(workspace_only=workspace_only)}
        )

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_openclaw(self) -> dict[str, Any]:
        """Serialize to OpenClaw's camelCase JSON payload."""
        out: dict[str, Any] = {"profile": self.profile}

        if self.allow:
            out["allow"] = list(self.allow)
        if self.deny_list:
            out["deny"] = list(self.deny_list)
        if self.also_allow:
            out["alsoAllow"] = list(self.also_allow)

        out["exec"] = {
            "security": self.exec_policy.security,
            "ask": self.exec_policy.ask,
        }
        out["fs"] = {"workspaceOnly": self.fs.workspace_only}
        out["elevated"] = {
            "enabled": self.elevated.enabled,
            "allowFrom": list(self.elevated.allow_from),
        }
        out["web"] = {
            "search": {"provider": self.web.search.provider},
            "fetch": {"enabled": self.web.fetch.enabled},
        }

        return out

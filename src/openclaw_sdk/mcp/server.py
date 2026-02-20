"""MCP server configuration models for OpenClaw agents."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class StdioMcpServer(BaseModel):
    """MCP server via subprocess (stdio transport)."""

    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)

    def to_openclaw(self) -> dict[str, Any]:
        """Serialize to OpenClaw config format."""
        result: dict[str, Any] = {"command": self.command, "args": self.args}
        if self.env:
            result["env"] = self.env
        return result


class HttpMcpServer(BaseModel):
    """MCP server via HTTP (streamable-http transport)."""

    transport: Literal["streamable-http"] = "streamable-http"
    url: str
    headers: dict[str, str] = Field(default_factory=dict)

    def to_openclaw(self) -> dict[str, Any]:
        """Serialize to OpenClaw config format."""
        result: dict[str, Any] = {"transport": self.transport, "url": self.url}
        if self.headers:
            result["headers"] = self.headers
        return result


class McpServer:
    """Factory for MCP server configurations.

    Usage::

        pg = McpServer.stdio("uvx", ["mcp-server-postgres", "--conn", "..."])
        remote = McpServer.http(
            "http://10.0.0.42:3721/mcp",
            headers={"Authorization": "Bearer xxx"},
        )
    """

    @staticmethod
    def stdio(
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> StdioMcpServer:
        """Create a stdio-transport MCP server configuration."""
        return StdioMcpServer(command=command, args=args or [], env=env or {})

    @staticmethod
    def http(
        url: str,
        headers: dict[str, str] | None = None,
    ) -> HttpMcpServer:
        """Create an HTTP-transport MCP server configuration."""
        return HttpMcpServer(url=url, headers=headers or {})

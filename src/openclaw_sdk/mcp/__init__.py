"""MCP (Model Context Protocol) server configuration."""

from __future__ import annotations

from openclaw_sdk.mcp.server import HttpMcpServer, McpServer, StdioMcpServer

__all__ = ["McpServer", "StdioMcpServer", "HttpMcpServer"]

"""Tests for MCP server configuration models."""

from __future__ import annotations

from openclaw_sdk.mcp.server import HttpMcpServer, McpServer, StdioMcpServer


class TestMcpServerStdioFactory:
    """Tests for McpServer.stdio() factory method."""

    def test_creates_stdio_server_with_correct_fields(self) -> None:
        server = McpServer.stdio("uvx", ["mcp-server-postgres", "--conn", "pg://"])
        assert isinstance(server, StdioMcpServer)
        assert server.command == "uvx"
        assert server.args == ["mcp-server-postgres", "--conn", "pg://"]

    def test_default_args_and_env_are_empty(self) -> None:
        server = McpServer.stdio("node")
        assert server.args == []
        assert server.env == {}

    def test_with_env(self) -> None:
        server = McpServer.stdio("npx", env={"NODE_ENV": "production"})
        assert server.env == {"NODE_ENV": "production"}


class TestMcpServerHttpFactory:
    """Tests for McpServer.http() factory method."""

    def test_creates_http_server_with_correct_fields(self) -> None:
        server = McpServer.http(
            "http://10.0.0.42:3721/mcp",
            headers={"Authorization": "Bearer xxx"},
        )
        assert isinstance(server, HttpMcpServer)
        assert server.url == "http://10.0.0.42:3721/mcp"
        assert server.headers == {"Authorization": "Bearer xxx"}

    def test_default_transport_is_streamable_http(self) -> None:
        server = McpServer.http("http://localhost:3000/mcp")
        assert server.transport == "streamable-http"

    def test_default_headers_are_empty(self) -> None:
        server = McpServer.http("http://localhost:3000/mcp")
        assert server.headers == {}


class TestStdioMcpServerToOpenclaw:
    """Tests for StdioMcpServer.to_openclaw() serialization."""

    def test_correct_output(self) -> None:
        server = StdioMcpServer(
            command="uvx",
            args=["mcp-server-postgres"],
            env={"PG_CONN": "pg://localhost/db"},
        )
        result = server.to_openclaw()
        assert result == {
            "command": "uvx",
            "args": ["mcp-server-postgres"],
            "env": {"PG_CONN": "pg://localhost/db"},
        }

    def test_omits_empty_env(self) -> None:
        server = StdioMcpServer(command="node", args=["server.js"])
        result = server.to_openclaw()
        assert result == {"command": "node", "args": ["server.js"]}
        assert "env" not in result


class TestHttpMcpServerToOpenclaw:
    """Tests for HttpMcpServer.to_openclaw() serialization."""

    def test_correct_output(self) -> None:
        server = HttpMcpServer(
            url="http://10.0.0.42:3721/mcp",
            headers={"Authorization": "Bearer tok"},
        )
        result = server.to_openclaw()
        assert result == {
            "transport": "streamable-http",
            "url": "http://10.0.0.42:3721/mcp",
            "headers": {"Authorization": "Bearer tok"},
        }

    def test_omits_empty_headers(self) -> None:
        server = HttpMcpServer(url="http://localhost:3000/mcp")
        result = server.to_openclaw()
        assert result == {
            "transport": "streamable-http",
            "url": "http://localhost:3000/mcp",
        }
        assert "headers" not in result


class TestPydanticModelBehavior:
    """Tests that both models work as proper Pydantic models."""

    def test_stdio_round_trip(self) -> None:
        server = StdioMcpServer(
            command="uvx",
            args=["mcp-server-postgres"],
            env={"KEY": "val"},
        )
        data = server.model_dump()
        restored = StdioMcpServer.model_validate(data)
        assert restored == server

    def test_http_round_trip(self) -> None:
        server = HttpMcpServer(
            url="http://example.com/mcp",
            headers={"X-Api-Key": "secret"},
        )
        data = server.model_dump()
        restored = HttpMcpServer.model_validate(data)
        assert restored == server

    def test_stdio_json_round_trip(self) -> None:
        server = StdioMcpServer(command="node", args=["index.js"])
        json_str = server.model_dump_json()
        restored = StdioMcpServer.model_validate_json(json_str)
        assert restored == server

    def test_http_json_round_trip(self) -> None:
        server = HttpMcpServer(url="http://example.com/mcp")
        json_str = server.model_dump_json()
        restored = HttpMcpServer.model_validate_json(json_str)
        assert restored == server

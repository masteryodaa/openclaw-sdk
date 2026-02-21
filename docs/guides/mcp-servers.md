# MCP Servers

The Model Context Protocol (MCP) lets you extend an agent's capabilities by connecting
external tool servers. An MCP server exposes tools, resources, and prompts that the agent
can discover and invoke at runtime — without modifying the agent's core configuration.

## Transports

OpenClaw supports two MCP transport types.

| Transport | Use Case | Connection |
|-----------|----------|------------|
| **stdio** | Local CLI tools, npx packages | Spawns a child process |
| **HTTP**  | Remote services, shared servers | HTTP/SSE connection |

## Stdio Servers

Stdio MCP servers run as local child processes. The SDK spawns the command and
communicates over stdin/stdout.

```python
from openclaw_sdk import McpServer, StdioMcpServer

# Using the factory method (recommended)
server = McpServer.stdio(
    cmd="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem"],
    env={"HOME": "/home/user"},
)

# Or construct directly
server = StdioMcpServer(
    cmd="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem"],
    env={"HOME": "/home/user"},
)
```

!!! tip
    Use `npx -y` to auto-install npm-based MCP servers on first run. The `-y` flag
    skips the install confirmation prompt.

### Common Stdio Servers

```python
from openclaw_sdk import McpServer

# Filesystem access
fs_server = McpServer.stdio(
    cmd="npx",
    args=["-y", "@modelcontextprotocol/server-filesystem", "/path/to/workspace"],
)

# GitHub integration
github_server = McpServer.stdio(
    cmd="npx",
    args=["-y", "@modelcontextprotocol/server-github"],
    env={"GITHUB_TOKEN": "ghp_..."},
)

# PostgreSQL
pg_server = McpServer.stdio(
    cmd="npx",
    args=["-y", "@modelcontextprotocol/server-postgres"],
    env={"DATABASE_URL": "postgresql://localhost/mydb"},
)
```

## HTTP Servers

HTTP MCP servers run as standalone services and communicate over HTTP with
Server-Sent Events (SSE) for streaming.

```python
from openclaw_sdk import McpServer, HttpMcpServer

# Using the factory method (recommended)
server = McpServer.http(
    url="http://localhost:3000/mcp",
    headers={"Authorization": "Bearer sk-..."},
)

# Or construct directly
server = HttpMcpServer(
    url="http://localhost:3000/mcp",
    headers={"Authorization": "Bearer sk-..."},
)
```

!!! note
    HTTP MCP servers must be started independently before the agent connects.
    The SDK does not manage the lifecycle of remote MCP servers.

## Adding Servers to an Agent

Use `agent.add_mcp_server()` to register an MCP server with a running agent.

```python
import asyncio
from openclaw_sdk import OpenClawClient, McpServer

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = await client.get_agent("my-agent")

        # Add a stdio MCP server
        fs_server = McpServer.stdio(
            cmd="npx",
            args=["-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
        )
        await agent.add_mcp_server("filesystem", fs_server)

        # Add an HTTP MCP server
        api_server = McpServer.http(url="http://localhost:3000/mcp")
        await agent.add_mcp_server("custom-api", api_server)

        # The agent can now use tools from both servers
        response = await agent.chat("List all files in the workspace.")
        print(response.text)

asyncio.run(main())
```

## Removing Servers

Remove a previously registered MCP server by name.

```python
await agent.remove_mcp_server("filesystem")
```

!!! warning
    Removing an MCP server while the agent is mid-execution may cause tool calls
    to fail. Remove servers only between conversations or during idle periods.

## Environment Variables

Stdio servers often need environment variables for API keys and configuration.
Pass them via the `env` parameter — they are forwarded to the child process.

```python
from openclaw_sdk import McpServer

server = McpServer.stdio(
    cmd="npx",
    args=["-y", "@modelcontextprotocol/server-slack"],
    env={
        "SLACK_BOT_TOKEN": "xoxb-...",
        "SLACK_TEAM_ID": "T0123456789",
    },
)
```

!!! warning
    Never hard-code secrets in source files. Load them from environment variables
    or a secrets manager at runtime.

## Full Example

```python
import asyncio
import os
from openclaw_sdk import OpenClawClient, McpServer

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = await client.get_agent("research-agent")

        # Add GitHub tools
        await agent.add_mcp_server(
            "github",
            McpServer.stdio(
                cmd="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                env={"GITHUB_TOKEN": os.environ["GITHUB_TOKEN"]},
            ),
        )

        # Add a custom internal API
        await agent.add_mcp_server(
            "internal-api",
            McpServer.http(
                url="https://tools.internal.example.com/mcp",
                headers={"Authorization": f"Bearer {os.environ['API_KEY']}"},
            ),
        )

        # Agent discovers tools automatically
        response = await agent.chat(
            "Find open issues labeled 'bug' in the acme/widgets repo "
            "and cross-reference them with our internal tracker."
        )
        print(response.text)

        # Clean up
        await agent.remove_mcp_server("github")
        await agent.remove_mcp_server("internal-api")

asyncio.run(main())
```

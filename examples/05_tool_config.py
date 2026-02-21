# RUN: python examples/05_tool_config.py
"""Tool policy configuration — control what tools your agents can use.

Demonstrates: ToolPolicy presets, fluent builders, MCP servers,
and runtime policy changes via agent.set_tool_policy().
"""

import asyncio
import json

from openclaw_sdk import OpenClawClient, ClientConfig, AgentConfig, ToolPolicy
from openclaw_sdk.mcp.server import McpServer
from openclaw_sdk.gateway.mock import MockGateway


async def main() -> None:
    # --- Preset profiles ---
    print("Tool Policy Presets")
    print("=" * 50)

    minimal = ToolPolicy.minimal()
    coding = ToolPolicy.coding()
    full = ToolPolicy.full()

    for name, policy in [("minimal", minimal), ("coding", coding), ("full", full)]:
        print(f"\n  {name}:")
        print(f"    {json.dumps(policy.to_openclaw(), indent=4)}")

    # --- Fluent builders ---
    print("\n" + "=" * 50)
    print("Fluent Builders (immutable chaining)")
    print("=" * 50)

    # Start from coding preset, deny browser access, restrict filesystem
    safe_coding = (
        ToolPolicy.coding()
        .deny("browser", "canvas")
        .with_fs(workspace_only=True)
        .with_exec(security="deny")
    )
    print(f"\n  coding + deny browser/canvas + workspace-only FS + no exec:")
    print(f"    {json.dumps(safe_coding.to_openclaw(), indent=4)}")

    # --- MCP Server configuration ---
    print("\n" + "=" * 50)
    print("MCP Server Configuration")
    print("=" * 50)

    postgres = McpServer.stdio("uvx", ["mcp-server-postgres", "--conn", "postgresql://..."])
    github = McpServer.stdio(
        "npx", ["-y", "@modelcontextprotocol/server-github"],
        env={"GITHUB_TOKEN": "ghp_example"},
    )
    remote = McpServer.http(
        "http://10.0.0.42:3721/mcp",
        headers={"Authorization": "Bearer xxx"},
    )

    for name, server in [("postgres", postgres), ("github", github), ("remote", remote)]:
        print(f"\n  {name}:")
        print(f"    {json.dumps(server.to_openclaw(), indent=4)}")

    # --- Create agent with policy + MCP servers ---
    print("\n" + "=" * 50)
    print("Creating Agent with ToolPolicy + MCP Servers")
    print("=" * 50)

    mock = MockGateway()
    await mock.connect()
    mock.register("config.get", {"raw": "{}", "exists": True, "path": "/mock"})
    mock.register("config.set", {"ok": True})
    mock.register("config.patch", {"ok": True})

    client = OpenClawClient(config=ClientConfig(), gateway=mock)

    agent = await client.create_agent(AgentConfig(
        agent_id="data-bot",
        name="Data Analyst",
        system_prompt="You are an expert data analyst.",
        tool_policy=safe_coding,
        mcp_servers={"postgres": postgres, "github": github},
    ))
    print(f"\n  Created agent: {agent.agent_id}")

    # --- Runtime policy change ---
    print("\n  Changing tool policy at runtime...")
    await agent.set_tool_policy(ToolPolicy.full())
    print("  Policy changed to 'full' profile")

    # --- Runtime deny/allow ---
    await agent.deny_tools("exec", "sudo")
    print("  Denied: exec, sudo")

    await agent.allow_tools("custom-analyzer")
    print("  Allowed: custom-analyzer")

    # --- Runtime MCP server add/remove ---
    await agent.add_mcp_server("remote-api", remote)
    print("  Added MCP server: remote-api")

    await agent.remove_mcp_server("remote-api")
    print("  Removed MCP server: remote-api")

    await client.close()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())

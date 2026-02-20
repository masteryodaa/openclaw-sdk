# RUN: python examples/05_tool_config.py
"""Tool configuration — build typed tool configs and apply them at runtime.

Demonstrates: static AgentConfig tool wiring + dynamic agent.configure_tools().
"""

import asyncio
import json

from openclaw_sdk import OpenClawClient, ClientConfig, AgentConfig
from openclaw_sdk.gateway.mock import MockGateway
from openclaw_sdk.tools.config import (
    BrowserToolConfig,
    DatabaseToolConfig,
    FileToolConfig,
    ShellToolConfig,
    WebSearchToolConfig,
)


async def main() -> None:
    # Build individual tool configurations
    db_tool = DatabaseToolConfig(
        connection_string="postgresql://user:pass@localhost:5432/sales",
        allowed_tables=["orders", "products", "customers"],
        read_only=True,
    )

    file_tool = FileToolConfig(
        output_dir="/tmp/agent-outputs",
        allowed_formats=["csv", "json", "xlsx", "pdf"],
        max_file_size_mb=50,
    )

    browser_tool = BrowserToolConfig(
        headless=True,
        allowed_domains=["example.com", "docs.python.org"],
        timeout_seconds=30,
    )

    # allowed_commands=None -> all commands allowed (trusted agent)
    # allowed_commands=[]   -> no commands allowed (untrusted/sandboxed agent)
    shell_tool = ShellToolConfig(
        allowed_commands=["ls", "cat", "grep", "python"],
        working_directory="/workspace",
    )

    web_search_tool = WebSearchToolConfig(
        search_engine="google",
        max_results=5,
    )

    # Wire tool configs into an AgentConfig (static configuration)
    agent_config = AgentConfig(
        agent_id="data-analyst",
        name="Data Analyst",
        system_prompt="You are an expert data analyst. Use tools to answer data questions.",
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-20250514",
        tools=["database", "files", "browser", "shell", "web_search"],
        permission_mode="accept",
    )

    print("AgentConfig:")
    print(json.dumps(agent_config.model_dump(), indent=2, default=str))

    print("\nTool Configurations:")
    for name, tool in [
        ("DatabaseToolConfig", db_tool),
        ("FileToolConfig", file_tool),
        ("BrowserToolConfig", browser_tool),
        ("ShellToolConfig", shell_tool),
        ("WebSearchToolConfig", web_search_tool),
    ]:
        print(f"\n  {name}:")
        config_dict = tool.model_dump()
        for k, v in config_dict.items():
            print(f"    {k}: {v!r}")

    # --- Dynamic tool configuration at runtime ---
    print("\n" + "=" * 50)
    print("Dynamic tool configuration with agent.configure_tools()")
    print("=" * 50)

    mock = MockGateway()
    await mock.connect()
    mock.register("config.setTools", {"ok": True, "tools": ["database", "files"]})

    client = OpenClawClient(config=ClientConfig(), gateway=mock)
    agent = client.get_agent("data-analyst")

    # Apply tools to a running agent via the gateway
    result = await agent.configure_tools([db_tool, file_tool])
    print(f"\n  configure_tools() result: {result}")
    print("  Tools applied at runtime without restarting the agent.")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())

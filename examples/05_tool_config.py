# RUN: python examples/05_tool_config.py
"""Tool configuration — build AgentConfig with typed tool configs and print as JSON."""

import asyncio
import json

from openclaw_sdk import AgentConfig
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

    # Wire tool configs into an AgentConfig
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


if __name__ == "__main__":
    asyncio.run(main())

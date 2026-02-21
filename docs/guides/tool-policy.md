# Tool Policy

Tool policies control which tools an agent can use during execution. OpenClaw agents have
access to powerful capabilities — shell execution, file system access, web browsing, and
more. Tool policies let you lock down exactly what is permitted.

## Quick Start

```python
from openclaw_sdk import OpenClawClient, ToolPolicy

async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
    agent = await client.get_agent("my-agent")

    # Apply a restrictive policy
    policy = ToolPolicy.minimal()
    await agent.set_tool_policy(policy)
```

## Policy Presets

The SDK ships four presets that cover common use cases.

| Preset                  | Shell | File System | Web | Messaging |
|-------------------------|-------|-------------|-----|-----------|
| `ToolPolicy.minimal()`  | No    | Read-only   | No  | No        |
| `ToolPolicy.coding()`   | Sandboxed | Workspace | No | No       |
| `ToolPolicy.messaging()`| No    | No          | No  | Yes       |
| `ToolPolicy.full()`     | Yes   | Yes         | Yes | Yes       |

```python
from openclaw_sdk import ToolPolicy

# Safe for untrusted prompts — no shell, no web, read-only files
minimal = ToolPolicy.minimal()

# Software engineering tasks — sandboxed shell, workspace-scoped files
coding = ToolPolicy.coding()

# Chat-only agents — messaging channels enabled, nothing else
messaging = ToolPolicy.messaging()

# Unrestricted — use with caution
full = ToolPolicy.full()
```

!!! warning
    `ToolPolicy.full()` grants the agent unrestricted access to all tools including
    shell execution and file writes. Only use this in trusted, sandboxed environments.

## Fluent Builders

Every preset returns a `ToolPolicy` instance you can further customize with fluent
method chaining.

```python
from openclaw_sdk import ToolPolicy

policy = (
    ToolPolicy.coding()
    .deny("browser", "messaging")
    .allow_tools("web_search", "calculator")
)
```

- **`policy.deny(*tool_names)`** — block specific tools by name.
- **`policy.allow_tools(*tool_names)`** — explicitly permit specific tools.
- **`policy.deny_all()`** — block every tool (useful as a starting point).

!!! tip
    Chain `.deny()` and `.allow_tools()` to build allowlist-style policies:
    `ToolPolicy.minimal().allow_tools("web_search")` permits only web search.

## Sub-Policies

For fine-grained control, configure individual capability domains using sub-policy
objects.

```python
from openclaw_sdk import ToolPolicy, ExecPolicy, FsPolicy, ElevatedPolicy, WebPolicy

policy = (
    ToolPolicy.coding()
    .with_exec(ExecPolicy(security="sandboxed", timeout=30))
    .with_fs(FsPolicy(workspace_only=True, allow_hidden=False))
    .with_elevated(ElevatedPolicy(enabled=False))
    .with_web(WebPolicy(allowed_domains=["docs.python.org"]))
)
```

| Sub-Policy       | Controls                                      |
|------------------|-----------------------------------------------|
| `ExecPolicy`     | Shell execution — sandboxing, timeouts         |
| `FsPolicy`       | File system — workspace scope, hidden files    |
| `ElevatedPolicy` | Privileged operations — sudo, admin actions    |
| `WebPolicy`      | Web access — domain allowlists, browsing       |

### Shorthand Syntax

You can also pass keyword arguments directly instead of constructing sub-policy objects.

```python
policy = (
    ToolPolicy.coding()
    .with_exec(security="sandboxed", timeout=30)
    .with_fs(workspace_only=True)
)
```

## Agent Runtime Methods

Apply policies to a running agent, or toggle individual tools on the fly.

```python
from openclaw_sdk import OpenClawClient, ToolPolicy

async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
    agent = await client.get_agent("my-agent")

    # Set a full policy object
    await agent.set_tool_policy(ToolPolicy.coding())

    # Quick deny/allow without rebuilding the whole policy
    await agent.deny_tools("shell", "browser")
    await agent.allow_tools("web_search")
```

!!! note
    `agent.deny_tools()` and `agent.allow_tools()` modify the agent's **current**
    policy in-place on the server. They do not replace the entire policy.

## Serialization

`ToolPolicy` is a Pydantic model that serializes directly to OpenClaw's native
camelCase configuration format. You can inspect or persist the policy as JSON.

```python
from openclaw_sdk import ToolPolicy

policy = ToolPolicy.coding().with_exec(security="sandboxed")

# Serialize to camelCase JSON for OpenClaw
print(policy.model_dump(by_alias=True))
# {"exec": {"security": "sandboxed"}, "fs": {"workspaceOnly": true}, ...}

# Round-trip from JSON
restored = ToolPolicy.model_validate_json(policy.model_dump_json(by_alias=True))
```

## Full Example

```python
import asyncio
from openclaw_sdk import OpenClawClient, ToolPolicy, ExecPolicy, FsPolicy

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = await client.get_agent("code-reviewer")

        # Build a policy: sandboxed shell, workspace files only, no web
        policy = (
            ToolPolicy.minimal()
            .with_exec(ExecPolicy(security="sandboxed", timeout=60))
            .with_fs(FsPolicy(workspace_only=True))
            .deny("browser", "messaging")
            .allow_tools("shell", "file_read", "file_write")
        )

        await agent.set_tool_policy(policy)
        response = await agent.chat("Review the code in src/ for security issues.")
        print(response.text)

asyncio.run(main())
```

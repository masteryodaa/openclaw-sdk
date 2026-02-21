# Agent Templates

Pre-built agent configurations for common use cases. Create production-ready agents in one line.

## Quick Start

```python
from openclaw_sdk import get_template, list_templates

# See available templates
print(list_templates())
# ['assistant', 'code-reviewer', 'customer-support', 'data-analyst',
#  'devops', 'mobile-jarvis', 'researcher', 'writer']

# Create an agent from a template
agent = await client.create_agent_from_template("customer-support")
result = await agent.execute("How do I reset my password?")
```

## Available Templates

| Template | Tools | Channels | Description |
|----------|-------|----------|-------------|
| `assistant` | Coding | — | General-purpose helpful assistant |
| `customer-support` | Minimal | WhatsApp, Telegram | Friendly support agent with escalation |
| `data-analyst` | Coding | — | Data analysis and visualization |
| `code-reviewer` | Coding | — | Bug detection and code quality review |
| `researcher` | Full | — | Multi-source research with citations |
| `writer` | Minimal | — | SEO-optimized content creation |
| `devops` | Full (confirm) | — | Server monitoring and deployment |
| `mobile-jarvis` | Full (confirm) | — | Android/Termux mobile assistant with memory |

## Customizing Templates

Override any field when creating from a template:

```python
# Custom agent ID
agent = await client.create_agent_from_template(
    "customer-support",
    agent_id="acme-support",
)

# Override model and channels
agent = await client.create_agent_from_template(
    "data-analyst",
    agent_id="my-analyst",
    llm_model="gpt-4o",
    channels=["slack"],
)
```

## Getting Template Config

Inspect a template's configuration without creating an agent:

```python
from openclaw_sdk import get_template

config = get_template("devops")
print(config.system_prompt)
print(config.tool_policy)
print(config.permission_mode)  # "confirm"
```

## Creating Custom Templates

Templates are just `AgentConfig` objects. Create your own:

```python
from openclaw_sdk import AgentConfig
from openclaw_sdk.tools.policy import ToolPolicy

my_template = AgentConfig(
    agent_id="my-bot",
    system_prompt="You are a specialized bot for my company.",
    tool_policy=ToolPolicy.coding().deny("browser"),
    channels=["slack"],
    enable_memory=True,
)

agent = await client.create_agent(my_template)
```

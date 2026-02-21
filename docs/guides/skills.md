# Skills & ClawHub

Skills are reusable capability packages that extend what an agent can do. ClawHub is
the public marketplace for discovering and installing community-built skills. Together,
they let you compose agent capabilities without writing custom tool code.

!!! note
    Skills and ClawHub are CLI-only features in OpenClaw. They are **not** available
    through the gateway WebSocket RPC. The SDK provides manager classes that wrap
    the CLI interface for convenience.

## Skill Manager

The `SkillManager` is available as `client.skills` and provides methods to manage
installed skills.

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        skills = client.skills

        # List all installed skills
        installed = await skills.list_skills()
        for skill in installed:
            print(f"{skill.name} — enabled: {skill.enabled}")

        # Install a new skill
        await skills.install_skill("web-researcher")

        # Enable / disable
        await skills.enable_skill("web-researcher")
        await skills.disable_skill("web-researcher")

        # Uninstall
        await skills.uninstall_skill("web-researcher")

asyncio.run(main())
```

### Skill Manager Methods

| Method | Description |
|--------|-------------|
| `list_skills()` | Returns all installed skills |
| `install_skill(name)` | Installs a skill from ClawHub |
| `uninstall_skill(name)` | Removes an installed skill |
| `enable_skill(name)` | Activates a disabled skill |
| `disable_skill(name)` | Deactivates a skill without uninstalling |

## ClawHub

ClawHub is the community marketplace. Use `client.clawhub` to browse and search
for skills.

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        hub = client.clawhub

        # Search for skills
        results = await hub.search("database")
        for skill in results:
            print(f"{skill.name}: {skill.description}")

        # Browse by category
        dev_tools = await hub.browse("developer-tools")

        # Get detailed info
        details = await hub.get_details("web-researcher")
        print(details.readme)

        # Discover categories
        categories = await hub.get_categories()
        print(categories)

        # See what is popular
        trending = await hub.get_trending()
        for skill in trending:
            print(f"{skill.name} — {skill.downloads} downloads")

asyncio.run(main())
```

### ClawHub Methods

| Method | Description |
|--------|-------------|
| `search(query)` | Full-text search across all published skills |
| `browse(category)` | List skills in a specific category |
| `get_details(name)` | Fetch full metadata, readme, and version info |
| `get_categories()` | List all available skill categories |
| `get_trending()` | Return currently trending skills |

## Skills Configuration

Use `SkillsConfig` to configure skill behavior at the client level.

```python
from openclaw_sdk import SkillsConfig, SkillLoadConfig, SkillInstallConfig

config = SkillsConfig(
    hub=True,                          # Enable ClawHub integration
    load=SkillLoadConfig(
        timeout=30,                    # Seconds to wait for skill init
        retry=3,                       # Retry failed loads
    ),
    install=SkillInstallConfig(
        auto_update=True,              # Keep skills up to date
        allow_prerelease=False,        # Stable releases only
    ),
)
```

## Per-Skill Configuration

Individual skills can require configuration — API keys, preferences, or feature flags.
Use `SkillEntry` to configure a specific skill on an agent.

```python
import asyncio
from openclaw_sdk import OpenClawClient, SkillEntry

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = await client.get_agent("my-agent")

        # Configure a skill with an API key
        entry = SkillEntry(enabled=True, api_key="sk-skill-...")
        await agent.configure_skill("web-researcher", entry)

        # Quick enable/disable on the agent
        await agent.enable_skill("web-researcher")
        await agent.disable_skill("web-researcher")

asyncio.run(main())
```

!!! tip
    Use `agent.enable_skill()` / `agent.disable_skill()` for quick toggles.
    Use `agent.configure_skill()` when you need to set API keys or options.

## Applying Skills Config to an Agent

Set the entire skills configuration at once with `agent.set_skills()`.

```python
from openclaw_sdk import SkillsConfig, SkillLoadConfig

config = SkillsConfig(
    hub=True,
    load=SkillLoadConfig(timeout=60),
)
await agent.set_skills(config)
```

## Full Example

```python
import asyncio
from openclaw_sdk import (
    OpenClawClient,
    SkillsConfig,
    SkillLoadConfig,
    SkillInstallConfig,
    SkillEntry,
)

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        # Browse ClawHub for a useful skill
        results = await client.clawhub.search("summarizer")
        if not results:
            print("No summarizer skills found.")
            return

        skill_name = results[0].name
        print(f"Installing {skill_name}...")
        await client.skills.install_skill(skill_name)

        # Configure skills on an agent
        agent = await client.get_agent("assistant")
        await agent.set_skills(
            SkillsConfig(
                hub=True,
                load=SkillLoadConfig(timeout=30, retry=2),
                install=SkillInstallConfig(auto_update=True),
            )
        )

        # Enable and configure the installed skill
        await agent.configure_skill(
            skill_name,
            SkillEntry(enabled=True),
        )

        response = await agent.chat("Summarize the latest project status.")
        print(response.text)

asyncio.run(main())
```

!!! warning
    Skill API keys are sent to the OpenClaw instance. Ensure your connection is
    secure (TLS in production) and that you trust the OpenClaw host.

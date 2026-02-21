# Prompt Versioning

Track, compare, and roll back system prompts across versions.

## Overview

`PromptStore` provides an in-memory versioned prompt store with tagging, diffing, and JSON export/import. Use it to version-control your prompts without external tools.

## Quick Start

```python
from openclaw_sdk import PromptStore

store = PromptStore()

# Save versions
store.save("greeter", "Hello, how can I help?")
store.save("greeter", "Hi there! What can I do for you today?", tags=["friendly"])

# Get latest
latest = store.get("greeter")
print(latest.content)   # "Hi there! ..."
print(latest.version)   # 2

# Get specific version
v1 = store.get("greeter", version=1)
print(v1.content)  # "Hello, how can I help?"
```

## Version History

```python
# List all versions
for v in store.list_versions("greeter"):
    print(f"v{v.version}: {v.content[:50]}... [{', '.join(v.tags)}]")

# List all prompt names
print(store.list_prompts())  # ["greeter"]
```

## Tagging

Organize versions with tags for A/B testing and categorization:

```python
store.save("support", "You are a support agent.", tags=["v1", "formal"])
store.save("support", "Hey! I'm here to help.", tags=["v2", "casual"])

# Find by tag
casual = store.get_by_tag("support", "casual")
print(casual[0].content)
```

## Comparing Versions

```python
diff = store.diff("greeter", 1, 2)
print(f"Same content: {diff['same']}")
print(f"V1: {diff['content_a']}")
print(f"V2: {diff['content_b']}")
print(f"Hash A: {diff['hash_a']}")
print(f"Hash B: {diff['hash_b']}")
```

## Rollback

Revert to a previous version (creates a new version from the old content):

```python
store.rollback("greeter", version=1)
latest = store.get("greeter")
print(latest.version)  # 3
print(latest.content)  # Same as v1
print(latest.tags)     # ["rollback", "from-v1"]
```

## Export & Import

Save prompts to JSON for backup or sharing:

```python
# Export
json_str = store.export_json()
with open("prompts.json", "w") as f:
    f.write(json_str)

# Import into a new store
new_store = PromptStore()
with open("prompts.json") as f:
    new_store.import_json(f.read())
```

## Using with Agents

Combine with `PromptTemplate` for dynamic prompts:

```python
from openclaw_sdk import PromptTemplate

# Version-controlled base prompt
store.save("analyst", "You are a {role} analyst. Focus on {domain}.")

# At runtime, get latest and render
latest = store.get("analyst")
template = PromptTemplate(latest.content)
prompt = template.render(role="senior", domain="market trends")

agent = await client.create_agent(AgentConfig(
    agent_id="analyst",
    system_prompt=prompt,
))
```

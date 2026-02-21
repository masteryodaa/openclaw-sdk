# Multi-tenancy

Serve multiple companies from one platform with isolated agents, quotas, and billing.

## Overview

`TenantWorkspace` provides tenant isolation, agent namespacing, model restrictions, and cost tracking. Each tenant gets their own agents that can't access other tenants' data.

## Quick Start

```python
from openclaw_sdk import TenantWorkspace, TenantConfig, AgentConfig

workspace = TenantWorkspace(client)

# Register tenants
workspace.register_tenant(TenantConfig(
    tenant_id="acme",
    name="Acme Corp",
    max_agents=5,
    max_cost_usd_per_day=10.0,
    allowed_models=["claude-sonnet-4-20250514", "gpt-4o-mini"],
))

# Create tenant-scoped agent
agent = await workspace.create_agent("acme", AgentConfig(
    agent_id="support",
    system_prompt="You are Acme Corp support.",
))
# Agent ID becomes "tenant-acme-support" (namespaced)

# Execute with quota enforcement
result = await workspace.execute("acme", "support", "Help me reset my password")
```

## Tenant Configuration

```python
from openclaw_sdk import TenantConfig

config = TenantConfig(
    tenant_id="globex",
    name="Globex Inc",
    max_agents=10,                    # Max agents per tenant
    max_queries_per_hour=1000,        # Rate limiting
    max_cost_usd_per_day=50.0,       # Daily spending cap
    allowed_models=["gpt-4o-mini"],  # Model whitelist
    allowed_tools=["web_search"],    # Tool restrictions
    metadata={"plan": "enterprise"}, # Custom metadata
)
```

## Quota Enforcement

The workspace automatically enforces quotas:

```python
# Agent limit
try:
    for i in range(20):
        await workspace.create_agent("acme", AgentConfig(agent_id=f"bot-{i}"))
except ValueError as e:
    print(e)  # "Tenant 'acme' has reached the agent limit (5)"

# Cost limit
try:
    # After many executions...
    await workspace.execute("acme", "support", "Another query")
except ValueError as e:
    print(e)  # "Tenant 'acme' has exceeded usage limits (cost: $10.50 / $10.00)"

# Model restriction
try:
    await workspace.create_agent("acme", AgentConfig(
        agent_id="premium",
        llm_model="claude-opus-4-20250514",
    ))
except ValueError as e:
    print(e)  # "Model 'claude-opus-4-20250514' not allowed for tenant 'acme'"
```

## Usage Reports

```python
report = workspace.get_usage_report("acme")
print(f"Tenant: {report['name']}")
print(f"Agents: {report['agents']} / {report['max_agents']}")
print(f"Queries: {report['total_queries']}")
print(f"Cost: ${report['total_cost_usd']:.2f} / ${report['max_cost_usd_per_day']:.2f}")
print(f"Utilization: {report['cost_utilization_pct']:.1f}%")
```

## Tenant Lifecycle

```python
# Deactivate (blocks new executions)
workspace.deactivate_tenant("acme")

# Re-activate
workspace.activate_tenant("acme")

# Reset daily counters (call from a daily cron job)
tenant = workspace.get_tenant("acme")
tenant.reset_daily_usage()
```

## SaaS Example

```python
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.post("/api/tenants/{tenant_id}/chat")
async def tenant_chat(tenant_id: str, query: str, agent_id: str = "support"):
    try:
        result = await workspace.execute(tenant_id, agent_id, query)
        return {"response": result.content}
    except KeyError:
        raise HTTPException(404, f"Tenant '{tenant_id}' not found")
    except ValueError as e:
        raise HTTPException(429, str(e))
```

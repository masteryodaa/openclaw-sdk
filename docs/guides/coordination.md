# Multi-agent Coordination

Orchestrate multiple agents with supervisor-worker patterns, consensus voting, and intelligent routing.

## Supervisor Pattern

Delegate tasks to worker agents with different execution strategies:

```python
from openclaw_sdk import Supervisor

supervisor = Supervisor(client, supervisor_agent_id="manager")
supervisor.add_worker("researcher", description="Research tasks")
supervisor.add_worker("writer", description="Writing tasks")
supervisor.add_worker("editor", description="Editing tasks")

# Sequential: each worker sees previous results
result = await supervisor.delegate(
    "Research AI trends and write a report",
    strategy="sequential",
)
print(result.final_result.content)
print(f"Workers used: {result.delegations}")
```

### Strategies

| Strategy | Description | Best For |
|----------|-------------|----------|
| `sequential` | Workers execute in order, each sees prior results | Multi-step workflows |
| `parallel` | All workers execute concurrently | Independent subtasks |
| `round-robin` | Workers try in order, first success wins | Redundancy / failover |

```python
# Parallel: all workers run at once
result = await supervisor.delegate("Analyze this data", strategy="parallel")

for agent_id, worker_result in result.worker_results.items():
    print(f"{agent_id}: {worker_result.content[:100]}")
```

## Consensus Voting

Run the same query through multiple agents and pick the consensus answer:

```python
from openclaw_sdk import ConsensusGroup

group = ConsensusGroup(client, ["analyst-1", "analyst-2", "analyst-3"])

result = await group.vote(
    "What is the capital of France?",
    method="majority",
)

print(f"Consensus: {result.chosen_result.content}")
print(f"Agreement: {result.agreement_ratio:.0%}")
print(f"Votes: {result.votes}")
```

### Voting Methods

| Method | Passes When |
|--------|-------------|
| `majority` | More than half agree |
| `unanimous` | All agents agree |
| `any` | At least one succeeds |

### Custom Scoring

Use a custom scorer to normalize responses before comparing:

```python
result = await group.vote(
    "What is 2 + 2?",
    scorer=lambda r: r.content.strip().lower(),
    method="majority",
)
```

## Agent Router

Route queries to the right agent based on content:

```python
from openclaw_sdk import AgentRouter

router = AgentRouter(client)
router.add_route(lambda q: "code" in q.lower(), "code-reviewer")
router.add_route(lambda q: "data" in q.lower(), "data-analyst")
router.add_route(lambda q: "write" in q.lower(), "writer")
router.set_default("general-assistant")

# Automatically routes to the right agent
result = await router.route("Review this Python code for bugs")
# Routes to "code-reviewer"
```

## Combining Patterns

Use coordination primitives together for complex workflows:

```python
# Router selects the team, Supervisor runs them
router = AgentRouter(client)
router.add_route(
    lambda q: "technical" in q.lower(),
    "tech-supervisor",
)
router.add_route(
    lambda q: "creative" in q.lower(),
    "creative-supervisor",
)

# Each supervisor manages its own team
tech_super = Supervisor(client)
tech_super.add_worker("backend-dev")
tech_super.add_worker("frontend-dev")
tech_super.add_worker("qa-engineer")
```

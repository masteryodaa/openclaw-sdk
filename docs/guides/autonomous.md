# Autonomous Agents

The OpenClaw SDK provides a goal-driven autonomous execution framework that lets agents
pursue high-level objectives iteratively, with built-in safety constraints and budget
tracking. Instead of issuing single queries, you describe a **Goal** and let a
**GoalLoop** drive the agent until the goal is achieved or resource limits are reached.
For multi-agent scenarios, the **Orchestrator** routes goals to the best-matching agent
based on registered capabilities.

## Quick Start

```python
import asyncio
from openclaw_sdk import OpenClawClient
from openclaw_sdk.autonomous import Goal, GoalLoop, Budget

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("assistant")

        goal = Goal(description="Summarize the latest AI safety research", max_steps=5)
        budget = Budget(max_cost_usd=1.00, max_tokens=50000)

        loop = GoalLoop(agent, goal, budget)
        completed_goal = await loop.run()

        print(f"Status: {completed_goal.status}")   # completed
        print(f"Result: {completed_goal.result}")

asyncio.run(main())
```

## Goal

A `Goal` describes what an agent should accomplish. Goals can be hierarchical -- a parent
goal may contain `sub_goals` that must be completed as part of the larger objective.

```python
from openclaw_sdk.autonomous import Goal, GoalStatus

# Simple goal
goal = Goal(description="Write a project README")

# Goal with sub-goals and custom step limit
goal = Goal(
    description="Build a complete test suite",
    max_steps=20,
    sub_goals=[
        Goal(description="Write unit tests for the API layer"),
        Goal(description="Write integration tests for the database"),
    ],
    metadata={"project": "my-app", "priority": "high"},
)
```

| Parameter     | Type               | Default              | Description                                        |
|---------------|--------------------|----------------------|----------------------------------------------------|
| `description` | `str`              | *required*           | Natural-language description of what to achieve     |
| `status`      | `GoalStatus`       | `GoalStatus.PENDING` | Current status of the goal                          |
| `sub_goals`   | `list[Goal]`       | `[]`                 | Optional child goals for decomposition              |
| `max_steps`   | `int`              | `10`                 | Maximum number of execution iterations              |
| `result`      | `str \| None`      | `None`               | Final result string once the goal completes or fails |
| `metadata`    | `dict[str, Any]`   | `{}`                 | Arbitrary key/value metadata attached to the goal   |

### GoalStatus

The `GoalStatus` enum tracks a goal through its lifecycle:

| Value         | Description                              |
|---------------|------------------------------------------|
| `PENDING`     | Goal has not started executing yet       |
| `IN_PROGRESS` | Goal is currently being worked on        |
| `COMPLETED`   | Goal was successfully accomplished       |
| `FAILED`      | Goal failed (budget exhausted, error, or max steps reached) |
| `CANCELLED`   | Goal was cancelled before completion     |

## GoalLoop

The `GoalLoop` is the core execution engine. It iteratively sends the goal description
to the agent, checks the response against an optional success predicate, updates budget
tracking, and stops when the goal succeeds, the budget is exhausted, or the maximum
number of steps is reached.

```python
from openclaw_sdk.autonomous import GoalLoop, Goal, Budget

goal = Goal(description="Find three peer-reviewed papers on transformer architectures")
budget = Budget(max_tokens=100000, max_duration_seconds=120)

# Basic loop -- succeeds on first successful execution
loop = GoalLoop(agent, goal, budget)
result = await loop.run()

# With a custom success predicate
loop = GoalLoop(
    agent, goal, budget,
    success_predicate=lambda r: "references" in r.content.lower(),
)
result = await loop.run()
```

| Parameter            | Type                                       | Default    | Description                                                 |
|----------------------|--------------------------------------------|------------|-------------------------------------------------------------|
| `agent`              | `Agent` (or any `_AgentLike`)              | *required* | The agent to execute queries against                         |
| `goal`               | `Goal`                                     | *required* | The goal to pursue                                           |
| `budget`             | `Budget`                                   | *required* | Resource limits governing execution                          |
| `success_predicate`  | `Callable[[ExecutionResult], bool] \| None` | `None`     | Custom check for goal completion; `None` means succeed on first successful execution |
| `on_step`            | `Callable[[int, ExecutionResult], None] \| None` | `None` | Callback invoked after every iteration with the step number and result |

### Execution Flow

Each iteration of the loop:

1. The **Watchdog** checks whether the budget is exhausted. If so, the goal is marked `FAILED` with `"Budget exhausted"`.
2. The agent's `execute()` method is called with `goal.description`.
3. Budget tracking fields are updated (duration, tokens, tool calls).
4. The optional `on_step` callback is invoked.
5. If the execution failed (`result.success is False`), the loop continues to the next step.
6. If a `success_predicate` is provided, the goal completes only when the predicate returns `True`. Without a predicate, the goal completes on the first successful execution.
7. If all `max_steps` are exhausted without success, the goal is marked `FAILED`.

### Step Callbacks

Use `on_step` to log progress or implement custom monitoring:

```python
def log_progress(step: int, result):
    print(f"Step {step}: success={result.success}, tokens={result.token_usage.total}")

loop = GoalLoop(agent, goal, budget, on_step=log_progress)
completed = await loop.run()
```

## Budget

The `Budget` model defines resource limits for autonomous execution. Each limit field
is optional -- `None` means unlimited for that dimension.

```python
from openclaw_sdk.autonomous import Budget

# Limit cost and tokens
budget = Budget(max_cost_usd=5.00, max_tokens=200000)

# Limit duration and tool calls
budget = Budget(max_duration_seconds=300, max_tool_calls=50)

# Full budget with all limits
budget = Budget(
    max_cost_usd=2.00,
    max_tokens=100000,
    max_duration_seconds=180,
    max_tool_calls=25,
)
```

| Parameter              | Type            | Default | Description                              |
|------------------------|-----------------|---------|------------------------------------------|
| `max_cost_usd`         | `float \| None` | `None`  | Maximum cost in USD                      |
| `max_tokens`           | `int \| None`   | `None`  | Maximum total token usage                |
| `max_duration_seconds`  | `float \| None` | `None`  | Maximum wall-clock time in seconds       |
| `max_tool_calls`       | `int \| None`   | `None`  | Maximum number of tool calls             |
| `cost_spent`           | `float`         | `0.0`   | Cost consumed so far (tracked automatically) |
| `tokens_spent`         | `int`           | `0`     | Tokens consumed so far                   |
| `duration_spent`       | `float`         | `0.0`   | Time consumed so far in seconds          |
| `tool_calls_spent`     | `int`           | `0`     | Tool calls consumed so far               |

### Budget Properties

```python
budget = Budget(max_cost_usd=5.00, max_tokens=100000)

# Check remaining resources
print(budget.remaining_cost)    # 5.0 (before any execution)
print(budget.remaining_tokens)  # 100000

# Check if any limit is exhausted
print(budget.is_exhausted)      # False
```

| Property           | Return Type      | Description                                   |
|--------------------|------------------|-----------------------------------------------|
| `is_exhausted`     | `bool`           | `True` when any configured limit has been reached |
| `remaining_cost`   | `float \| None`  | Remaining cost in USD, or `None` if unlimited  |
| `remaining_tokens` | `int \| None`    | Remaining tokens, or `None` if unlimited       |

## Watchdog

The `Watchdog` is a safety constraints checker that monitors a `Budget` and recommends
whether execution should continue, warn, or stop. The `GoalLoop` uses a `Watchdog`
internally, but you can also use it directly for custom execution loops.

```python
from openclaw_sdk.autonomous import Watchdog, WatchdogAction, Budget

budget = Budget(max_cost_usd=1.00, max_tokens=50000)
watchdog = Watchdog(budget)

action = watchdog.check()
if action == WatchdogAction.STOP:
    print("Budget exhausted -- stopping")
elif action == WatchdogAction.WARN:
    print("Over 80% of a limit consumed -- proceed with caution")
else:
    print("All clear -- continue execution")
```

| Action       | Condition                              |
|--------------|----------------------------------------|
| `CONTINUE`   | All limits are below 80% utilization   |
| `WARN`       | At least one limit is over 80% utilized |
| `STOP`       | At least one limit is fully exhausted   |

!!! tip "Warning threshold"
    The watchdog issues a `WARN` action when any limit reaches 80% utilization. This
    gives your application an opportunity to log, alert, or take corrective action
    before the budget is fully exhausted.

## Orchestrator

The `Orchestrator` manages goal execution across a pool of registered agents. It
maintains a registry of agent capabilities and routes goals to the best-matching agent
using keyword overlap between the goal description and agent skills.

```python
import asyncio
from openclaw_sdk import OpenClawClient
from openclaw_sdk.autonomous import Orchestrator, Goal, Budget

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        orch = Orchestrator(client)

        # Register agents with their capabilities
        orch.register_agent("researcher", "Deep research agent", ["research", "analysis", "papers"])
        orch.register_agent("writer", "Content writing agent", ["writing", "editing", "blog"])
        orch.register_agent("coder", "Code generation agent", ["code", "python", "testing"])

        # The orchestrator routes to the best-matching agent
        goal = Goal(description="Research recent advances in neural architecture search")
        budget = Budget(max_tokens=100000, max_cost_usd=2.00)

        completed = await orch.execute_goal(goal, budget)
        print(f"Status: {completed.status}")
        print(f"Result: {completed.result}")

asyncio.run(main())
```

### Registering Agents

Each agent is registered with an ID, description, and a list of skill keywords:

```python
orch.register_agent(
    agent_id="data-analyst",
    description="Analyzes datasets and generates insights",
    skills=["data", "analysis", "statistics", "visualization"],
)
```

| Parameter     | Type              | Default | Description                             |
|---------------|-------------------|---------|-----------------------------------------|
| `agent_id`    | `str`             | *required* | Unique agent identifier              |
| `description` | `str`             | `""`    | Human-readable description of the agent |
| `skills`      | `list[str] \| None` | `None` | List of skill keywords for routing     |

### Goal Routing

The `route_goal()` method finds the best agent by scoring each registered agent on how
many of its skills appear (case-insensitive substring match) in the goal description.
The agent with the highest score wins.

```python
goal = Goal(description="Analyze the sales data and create visualizations")
best_agent = orch.route_goal(goal)
print(best_agent)  # "data-analyst" (matches "data", "analysis", "visualization")
```

### Executing Goals

`execute_goal()` combines routing with execution. You can also bypass routing with
`agent_override`:

```python
# Automatic routing
completed = await orch.execute_goal(goal, budget)

# Force a specific agent
completed = await orch.execute_goal(goal, budget, agent_override="researcher")

# With a custom success predicate
completed = await orch.execute_goal(
    goal, budget,
    success_predicate=lambda r: len(r.content) > 500,
)
```

| Parameter            | Type                                        | Default    | Description                                 |
|----------------------|---------------------------------------------|------------|---------------------------------------------|
| `goal`               | `Goal`                                      | *required* | The goal to execute                          |
| `budget`             | `Budget`                                    | *required* | Resource budget for the execution            |
| `agent_override`     | `str \| None`                               | `None`     | Explicit agent ID (bypasses routing)         |
| `success_predicate`  | `Callable[[ExecutionResult], bool] \| None`  | `None`     | Optional predicate for goal completion       |

!!! warning "No matching agent"
    If no `agent_override` is provided and no registered agent matches the goal's
    description, `execute_goal()` raises a `ValueError`. Always register agents with
    relevant skill keywords, or use `agent_override` as a fallback.

## Full Example

Here is a complete example combining all components:

```python
import asyncio
from openclaw_sdk import OpenClawClient
from openclaw_sdk.autonomous import (
    Orchestrator, Goal, Budget, GoalLoop, Watchdog, WatchdogAction,
)

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        # Set up the orchestrator with multiple agents
        orch = Orchestrator(client)
        orch.register_agent("researcher", "Research agent", ["research", "papers", "analysis"])
        orch.register_agent("writer", "Writing agent", ["writing", "blog", "article"])

        # Define goals with a budget
        budget = Budget(
            max_cost_usd=3.00,
            max_tokens=150000,
            max_duration_seconds=300,
        )

        # Execute a research goal -- orchestrator routes to "researcher"
        research_goal = Goal(
            description="Research the top 5 trends in AI for 2025",
            max_steps=3,
        )
        result = await orch.execute_goal(research_goal, budget)
        print(f"Research: {result.status} -- {result.result[:100]}...")

        # Check remaining budget
        print(f"Budget remaining: ${budget.remaining_cost:.2f}")
        print(f"Tokens remaining: {budget.remaining_tokens}")

asyncio.run(main())
```

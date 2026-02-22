# Workflows

The workflow engine provides a branching state machine for orchestrating multi-step
agent processes. Unlike the linear `Pipeline` (which chains steps sequentially), a
`Workflow` supports conditional branching, human approval gates, context transforms,
and named step navigation -- making it suitable for complex business processes where
the next step depends on the outcome of the previous one.

## Quick Start

```python
import asyncio
from openclaw_sdk import OpenClawClient
from openclaw_sdk.workflows import Workflow, WorkflowStep, StepType

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        wf = Workflow("my-workflow", [
            WorkflowStep(
                name="draft",
                step_type=StepType.AGENT,
                config={"agent_id": "writer", "query": "Write a summary of: {topic}"},
            ),
            WorkflowStep(
                name="review",
                step_type=StepType.AGENT,
                config={"agent_id": "editor", "query": "Review and improve: {draft}"},
            ),
        ])

        result = await wf.run(
            {"topic": "The future of renewable energy"},
            agent_factory=lambda agent_id: client.get_agent(agent_id),
        )

        print(f"Success: {result.success}")
        print(f"Output:  {result.final_output}")
        print(f"Latency: {result.latency_ms}ms")

asyncio.run(main())
```

## Pipeline vs. Workflow

Both `Pipeline` and `Workflow` chain agent calls, but they serve different purposes:

| Feature                | Pipeline                    | Workflow                               |
|------------------------|-----------------------------|----------------------------------------|
| Execution model        | Strictly sequential         | Branching state machine                |
| Conditional routing    | Not supported               | `ConditionStep` with operators          |
| Human approval gates   | Not supported               | `ApprovalStep`                          |
| Context transforms     | Not supported               | `TransformStep` with functions/mappings |
| Step navigation        | Always next step            | `next_on_success` / `next_on_failure`  |
| Template variables     | `{step_name}` substitution  | `{key}` from shared context dict       |
| Best for               | Simple sequential chains    | Complex branching processes            |

!!! tip "When to use which"
    Use `Pipeline` when you have a simple chain of agent calls where each step feeds
    into the next. Use `Workflow` when you need branching, conditions, approvals, or
    dynamic routing between steps.

## WorkflowStep

Every step in a workflow is a `WorkflowStep` model with a type that determines how it
is executed.

```python
from openclaw_sdk.workflows import WorkflowStep, StepType

step = WorkflowStep(
    name="analyze",
    step_type=StepType.AGENT,
    config={"agent_id": "analyst", "query": "Analyze: {data}"},
    next_on_success="report",
    next_on_failure="retry",
)
```

| Parameter         | Type            | Default            | Description                                        |
|-------------------|-----------------|--------------------|----------------------------------------------------|
| `name`            | `str`           | *required*         | Unique identifier for the step                     |
| `step_type`       | `StepType`      | *required*         | Type of step (`AGENT`, `CONDITION`, `APPROVAL`, `TRANSFORM`) |
| `config`          | `dict[str, Any]`| `{}`               | Step-specific configuration (see below)            |
| `status`          | `StepStatus`    | `StepStatus.PENDING` | Current status (managed by the engine)           |
| `result`          | `Any`           | `None`             | Step result (set by the engine after execution)    |
| `next_on_success` | `str \| None`   | `None`             | Jump to this step name on success                  |
| `next_on_failure` | `str \| None`   | `None`             | Jump to this step name on failure                  |

### StepType

| Type        | Description                                                  |
|-------------|--------------------------------------------------------------|
| `AGENT`     | Calls an agent with a query template                         |
| `CONDITION` | Evaluates a condition on the shared context                  |
| `APPROVAL`  | Gates execution on human approval (or auto-approve)          |
| `TRANSFORM` | Applies a transformation function or key mapping to context  |

### StepStatus

| Status      | Description                          |
|-------------|--------------------------------------|
| `PENDING`   | Step has not started yet             |
| `RUNNING`   | Step is currently executing          |
| `COMPLETED` | Step finished successfully           |
| `FAILED`    | Step failed                          |
| `SKIPPED`   | Step was skipped (jumped over)       |

## Step Types in Detail

### Agent Steps

Agent steps call an agent with a query template. Template variables use `{key}` syntax
and are resolved from the shared context dict. The agent's response is stored in the
context under the step's name.

```python
WorkflowStep(
    name="research",
    step_type=StepType.AGENT,
    config={
        "agent_id": "researcher",
        "query": "Research the following topic: {topic}",
    },
)
```

**Config fields:**

| Key        | Type  | Description                                       |
|------------|-------|---------------------------------------------------|
| `agent_id` | `str` | The agent to execute the query against             |
| `query`    | `str` | Query template with `{variable}` placeholders      |

After execution, the agent's response content is stored in `context["research"]`
(using the step name as the key).

### Condition Steps

Condition steps evaluate a comparison against a value in the shared context and route
to different steps based on the outcome.

```python
WorkflowStep(
    name="check_quality",
    step_type=StepType.CONDITION,
    config={
        "key": "score",
        "operator": "gte",
        "value": 0.8,
    },
    next_on_success="publish",
    next_on_failure="revise",
)
```

**Config fields:**

| Key        | Type  | Description                              |
|------------|-------|------------------------------------------|
| `key`      | `str` | Context key to evaluate                  |
| `operator` | `str` | Comparison operator (see table below)    |
| `value`    | `Any` | Expected value to compare against        |

**Supported operators:**

| Operator   | Description               | Example                          |
|------------|---------------------------|----------------------------------|
| `eq`       | Equal to                  | `score == 0.8`                   |
| `ne`       | Not equal to              | `status != "failed"`             |
| `gt`       | Greater than              | `score > 0.5`                    |
| `gte`      | Greater than or equal to  | `score >= 0.8`                   |
| `lt`       | Less than                 | `attempts < 3`                   |
| `lte`      | Less than or equal to     | `cost <= 10.0`                   |
| `in`       | Value is in collection    | `category in ["a", "b"]`         |
| `contains` | String contains substring | `"error" in response`            |

### Approval Steps

Approval steps gate execution on human approval. In automated scenarios, use
`auto_approve` in the config.

```python
WorkflowStep(
    name="approve_publish",
    step_type=StepType.APPROVAL,
    config={"auto_approve": True},
    next_on_failure="revise",
)
```

**Config fields:**

| Key            | Type   | Default | Description                             |
|----------------|--------|---------|-----------------------------------------|
| `auto_approve` | `bool` | `False` | Whether to automatically approve        |

!!! note "Production approvals"
    In a production environment, the approval step would integrate with a human-in-the-loop
    system (e.g., Slack notification, email, or a dashboard button). The `auto_approve`
    flag is primarily for testing and automated pipelines.

### Transform Steps

Transform steps modify the shared context without calling an agent. They support two
modes: callable transforms and key mappings.

**Callable transform** -- a function that receives the context dict and returns new
values to merge:

```python
WorkflowStep(
    name="enrich",
    step_type=StepType.TRANSFORM,
    config={
        "transform": lambda ctx: {"word_count": len(ctx.get("draft", "").split())},
    },
)
```

**Key mapping** -- rename context keys:

```python
WorkflowStep(
    name="rename_keys",
    step_type=StepType.TRANSFORM,
    config={
        "mapping": {"research": "findings", "draft": "document"},
    },
)
```

**Config fields:**

| Key         | Type                     | Description                                      |
|-------------|--------------------------|--------------------------------------------------|
| `transform` | `Callable[[dict], dict]` | Function that receives context and returns a dict to merge |
| `mapping`   | `dict[str, str]`         | Rename keys: `{old_key: new_key}`                |

## Running a Workflow

The `run()` method executes the workflow with a shared context dict and an agent factory:

```python
result = await wf.run(
    context={"topic": "quantum computing", "audience": "beginners"},
    agent_factory=lambda agent_id: client.get_agent(agent_id),
)
```

| Parameter       | Type                                  | Default    | Description                                 |
|-----------------|---------------------------------------|------------|---------------------------------------------|
| `context`       | `dict[str, Any]`                      | *required* | Mutable dict shared across all steps        |
| `agent_factory` | `Callable[[str], AgentLike] \| None`  | `None`     | Factory that creates agents by ID (required for AGENT steps) |

Steps execute in insertion order unless `next_on_success` or `next_on_failure` redirects
to a different named step. On failure without a `next_on_failure` target, the workflow
stops immediately.

## WorkflowResult

The `run()` method returns a `WorkflowResult`:

```python
result = await wf.run(context, agent_factory=factory)

print(result.success)       # True if all executed steps succeeded
print(result.final_output)  # Result of the last executed step
print(result.latency_ms)    # Total wall-clock time in milliseconds

for step in result.steps:
    print(f"  {step.name}: {step.status} -> {step.result}")
```

| Field          | Type                 | Description                                  |
|----------------|----------------------|----------------------------------------------|
| `success`      | `bool`               | Whether the workflow completed without failures |
| `steps`        | `list[WorkflowStep]` | All steps with their final statuses and results |
| `final_output` | `Any`                | The result of the last executed step          |
| `latency_ms`   | `int`                | Total wall-clock time in milliseconds         |

## Branching Example

Here is a workflow with conditional branching -- the review feedback determines whether
the document is published or sent back for revision:

```python
import asyncio
from openclaw_sdk import OpenClawClient
from openclaw_sdk.workflows import Workflow, WorkflowStep, StepType

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        wf = Workflow("review-and-publish", [
            WorkflowStep(
                name="draft",
                step_type=StepType.AGENT,
                config={"agent_id": "writer", "query": "Write an article about: {topic}"},
            ),
            WorkflowStep(
                name="review",
                step_type=StepType.AGENT,
                config={"agent_id": "reviewer", "query": "Review this article: {draft}"},
            ),
            WorkflowStep(
                name="check_approved",
                step_type=StepType.CONDITION,
                config={"key": "review_approved", "operator": "eq", "value": True},
                next_on_success="publish",
                next_on_failure="revise",
            ),
            WorkflowStep(
                name="revise",
                step_type=StepType.AGENT,
                config={
                    "agent_id": "writer",
                    "query": "Revise this article based on feedback: {review}",
                },
            ),
            WorkflowStep(
                name="publish",
                step_type=StepType.TRANSFORM,
                config={
                    "transform": lambda ctx: {"published": True, "final_article": ctx.get("draft")},
                },
            ),
        ])

        result = await wf.run(
            {"topic": "Sustainable AI infrastructure", "review_approved": True},
            agent_factory=lambda agent_id: client.get_agent(agent_id),
        )

        print(f"Published: {result.success}")
        print(f"Output: {result.final_output}")

asyncio.run(main())
```

## Built-in Presets

The SDK includes three pre-built workflow configurations for common patterns. Each
preset returns a configured `Workflow` ready to run.

### review_workflow

A code or document review workflow with automatic revision on failure.

```python
from openclaw_sdk.workflows import review_workflow

wf = review_workflow(
    reviewer_agent_id="reviewer",
    author_agent_id="author",
)
result = await wf.run(
    {"document": "My draft document..."},
    agent_factory=lambda aid: client.get_agent(aid),
)
```

**Steps:** `review` (AGENT) -> `check_pass` (CONDITION on `review_passed`) -> `revise` (AGENT, on failure)

### research_workflow

A research-and-summarize workflow with a transform step to rename context keys.

```python
from openclaw_sdk.workflows import research_workflow

wf = research_workflow(
    researcher_agent_id="researcher",
    summarizer_agent_id="summarizer",
)
result = await wf.run(
    {"topic": "Quantum error correction"},
    agent_factory=lambda aid: client.get_agent(aid),
)
```

**Steps:** `research` (AGENT) -> `extract` (TRANSFORM: renames `research` to `findings`) -> `summarize` (AGENT)

### support_workflow

A customer support triage workflow that escalates high-priority issues.

```python
from openclaw_sdk.workflows import support_workflow

wf = support_workflow(
    triage_agent_id="triage",
    support_agent_id="support",
)
result = await wf.run(
    {"request": "My account was compromised and I need immediate help"},
    agent_factory=lambda aid: client.get_agent(aid),
)
```

**Steps:** `triage` (AGENT) -> `check_priority` (CONDITION on `priority == "high"`) -> `detailed_support` (AGENT, on failure)

!!! tip "Presets as starting points"
    The built-in presets are meant as starting points. Copy their step definitions and
    customize them for your specific use case -- add extra steps, change condition
    operators, or insert approval gates.

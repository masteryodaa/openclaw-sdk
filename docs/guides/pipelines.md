# Pipelines

Pipelines let you chain multiple agent calls into a sequential workflow where the output of one step feeds into the next. Each step uses a template with `{variable}` placeholders that are filled from previous step outputs or initial input variables.

## Creating a Pipeline

A `Pipeline` is initialized with an `OpenClawClient` and built up by adding steps. Each step specifies:

- **name** — A unique identifier for the step (used to reference its output in later templates).
- **agent_id** — Which agent to run for this step.
- **template** — The query template with `{placeholder}` variables.

```python
import asyncio
from openclaw_sdk import OpenClawClient, Pipeline

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        pipeline = Pipeline(client)

        pipeline.add_step(
            name="greet",
            agent_id="my-agent",
            template="Say hello to {name} in {language}.",
        )

        result = await pipeline.run(name="Alice", language="French")
        print(result.final_result.content)

asyncio.run(main())
```

## Template Variable Resolution

Templates use `{variable}` syntax. Variables are resolved in this order:

1. **Initial variables** — keyword arguments passed to `pipeline.run()`.
2. **Step outputs** — the `content` of a previous step's `ExecutionResult`, referenced by step name.

For example, `{topic}` resolves to the initial variable `topic`, while `{research}` resolves to the output of a step named `"research"`.

!!! note
    Step names must be valid Python identifiers (letters, digits, underscores) since they are used as template variable names. Choose descriptive names like `research`, `draft`, or `edit`.

## Multi-Step Example

Here is a three-step pipeline that researches a topic, writes an article, and then edits it:

```python
import asyncio
from openclaw_sdk import OpenClawClient, Pipeline

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        pipeline = Pipeline(client)

        # Step 1: Research the topic
        pipeline.add_step(
            name="research",
            agent_id="research-agent",
            template="Research the following topic thoroughly: {topic}. "
                     "Provide key facts, recent developments, and expert opinions.",
        )

        # Step 2: Write an article using the research
        pipeline.add_step(
            name="draft",
            agent_id="writer-agent",
            template="Write a 500-word article about {topic} for a {audience} audience. "
                     "Use the following research:\n\n{research}",
        )

        # Step 3: Edit the draft for clarity and style
        pipeline.add_step(
            name="edit",
            agent_id="editor-agent",
            template="Edit the following article for clarity, grammar, and style. "
                     "Target audience: {audience}. Keep the length under 500 words.\n\n{draft}",
        )

        result = await pipeline.run(
            topic="quantum computing breakthroughs in 2025",
            audience="general public",
        )

        # Final edited article
        print(result.final_result.content)

asyncio.run(main())
```

!!! tip
    You can use the same agent for multiple steps. For example, a general-purpose agent can handle both research and writing. Use different agents when you want specialized system prompts or model configurations for each role.

## PipelineResult

The `pipeline.run()` method returns a `PipelineResult` with these fields:

| Field | Type | Description |
|---|---|---|
| `final_result` | `ExecutionResult` | The result of the last step |
| `step_results` | `dict[str, ExecutionResult]` | Results keyed by step name |
| `total_latency_ms` | `float` | Sum of all step latencies |

You can inspect intermediate results to debug or log each step:

```python
import asyncio
from openclaw_sdk import OpenClawClient, Pipeline

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        pipeline = Pipeline(client)

        pipeline.add_step(
            name="outline",
            agent_id="my-agent",
            template="Create an outline for a blog post about {topic}.",
        )
        pipeline.add_step(
            name="write",
            agent_id="my-agent",
            template="Write the full blog post from this outline:\n\n{outline}",
        )

        result = await pipeline.run(topic="async Python best practices")

        # Inspect each step
        for step_name, step_result in result.step_results.items():
            print(f"--- {step_name} ---")
            print(f"Latency: {step_result.latency_ms:.0f}ms")
            print(f"Tokens: {step_result.token_usage.total}")
            print(f"Content preview: {step_result.content[:100]}...")
            print()

        print(f"Total pipeline latency: {result.total_latency_ms:.0f}ms")

asyncio.run(main())
```

## Using Different Agents Per Step

Pipelines shine when each step uses a different agent tuned for a specific task. For instance, you might have agents with different models, system prompts, or tool configurations:

```python
import asyncio
from openclaw_sdk import OpenClawClient, Pipeline

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        pipeline = Pipeline(client)

        # A fast model for classification
        pipeline.add_step(
            name="classify",
            agent_id="classifier-agent",
            template="Classify this support ticket into one category "
                     "(billing, technical, account, other): {ticket_text}",
        )

        # A capable model for drafting a response
        pipeline.add_step(
            name="respond",
            agent_id="support-agent",
            template="Draft a support response for a {classify} issue. "
                     "Original ticket: {ticket_text}",
        )

        # A specialized model for tone checking
        pipeline.add_step(
            name="review",
            agent_id="tone-checker",
            template="Review this support response for professional tone and empathy. "
                     "Fix any issues and return the final version.\n\n{respond}",
        )

        result = await pipeline.run(
            ticket_text="I was charged twice for my subscription last month "
                        "and I need a refund processed immediately.",
        )

        category = result.step_results["classify"].content
        print(f"Category: {category}")
        print(f"Final response:\n{result.final_result.content}")

asyncio.run(main())
```

## Error Handling

If any step fails, the pipeline raises the underlying exception. The `PipelineResult` is not returned for partial completions. Wrap the `run()` call in a try/except to handle failures:

```python
import asyncio
from openclaw_sdk import OpenClawClient, Pipeline
from openclaw_sdk.core.exceptions import ExecutionError

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        pipeline = Pipeline(client)
        pipeline.add_step(name="step1", agent_id="my-agent", template="Analyze {data}")
        pipeline.add_step(name="step2", agent_id="my-agent", template="Summarize: {step1}")

        try:
            result = await pipeline.run(data="quarterly revenue figures")
            print(result.final_result.content)
        except ExecutionError as e:
            print(f"Pipeline failed: {e}")

asyncio.run(main())
```

!!! warning
    Pipelines execute steps **sequentially**. If you need parallel execution of independent steps, use `agent.batch()` or `asyncio.gather()` instead.

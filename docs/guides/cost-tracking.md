# Cost Tracking

The `CostTracker` lets you monitor token usage and estimated costs across all your
agent runs. It aggregates data per agent and per model, supports export to CSV and
JSON, and ships with default pricing for common LLMs.

## Quick Start

```python
import asyncio
from openclaw_sdk import OpenClawClient
from openclaw_sdk.tracking.cost import CostTracker

async def main():
    tracker = CostTracker()

    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("assistant")

        result = await agent.execute("Explain quantum computing in one paragraph")
        tracker.record(result)

        result = await agent.execute("Now explain it for a five-year-old")
        tracker.record(result)

        summary = tracker.summary()
        print(f"Total input tokens:  {summary['total_input_tokens']}")
        print(f"Total output tokens: {summary['total_output_tokens']}")
        print(f"Estimated cost:      ${summary['total_cost_usd']:.4f}")

asyncio.run(main())
```

## Recording Results

Call `tracker.record(result)` after each `agent.execute()` call. The tracker
extracts token counts and model information from the `ExecutionResult`:

```python
result = await agent.execute("Hello, world!")
tracker.record(result)
```

Each recorded result contributes to the running totals for both the agent and
the model that served the request.

!!! tip "Record every result"
    For accurate cost tracking, call `tracker.record()` on every
    `ExecutionResult` you receive, including cached results (which will
    have zero tokens and zero cost).

## Cost Summary

The `summary()` method returns a dictionary with aggregate statistics:

```python
summary = tracker.summary()
```

The returned dictionary contains:

| Key                   | Type    | Description                              |
|-----------------------|---------|------------------------------------------|
| `total_input_tokens`  | `int`   | Sum of all input tokens across runs      |
| `total_output_tokens` | `int`   | Sum of all output tokens across runs     |
| `total_tokens`        | `int`   | Input + output tokens combined           |
| `total_cost_usd`      | `float` | Estimated total cost in USD              |
| `run_count`           | `int`   | Number of recorded runs                  |
| `by_agent`            | `dict`  | Breakdown keyed by agent ID              |
| `by_model`            | `dict`  | Breakdown keyed by model name            |

## Per-Agent and Per-Model Breakdown

The summary includes nested breakdowns so you can see which agents or models
consume the most resources:

```python
summary = tracker.summary()

# Per-agent breakdown
for agent_id, stats in summary["by_agent"].items():
    print(f"Agent {agent_id}: {stats['total_tokens']} tokens, ${stats['cost_usd']:.4f}")

# Per-model breakdown
for model, stats in summary["by_model"].items():
    print(f"Model {model}: {stats['total_tokens']} tokens, ${stats['cost_usd']:.4f}")
```

!!! note "Model detection"
    The model name comes from the `ExecutionResult.model` field, which is
    populated by the gateway. If the gateway does not report a model, the
    tracker records usage under the key `"unknown"`.

## Default Pricing

The tracker ships with built-in per-token pricing for common models:

| Model Family      | Input (per 1M tokens) | Output (per 1M tokens) |
|-------------------|-----------------------|------------------------|
| Claude Opus       | $15.00                | $75.00                 |
| Claude Sonnet     | $3.00                 | $15.00                 |
| Claude Haiku      | $0.25                 | $1.25                  |
| GPT-4o            | $2.50                 | $10.00                 |
| GPT-4 Turbo       | $10.00                | $30.00                 |

You can override pricing by passing a custom pricing dictionary:

```python
custom_pricing = {
    "my-fine-tuned-model": {
        "input_cost_per_million": 5.0,
        "output_cost_per_million": 15.0,
    }
}
tracker = CostTracker(pricing=custom_pricing)
```

## Exporting Data

Export accumulated tracking data for analysis or reporting:

```python
# Export as CSV
tracker.export_csv("costs.csv")

# Export as JSON
tracker.export_json("costs.json")
```

The CSV format includes one row per recorded run with columns for timestamp,
agent ID, model, input tokens, output tokens, and estimated cost.

The JSON export contains the full summary plus an array of individual run records.

!!! tip "Periodic exports"
    For long-running services, consider exporting periodically (e.g., hourly)
    and calling `tracker.reset()` to keep memory usage bounded.

## Resetting the Tracker

Clear all accumulated data and start fresh:

```python
tracker.reset()
summary = tracker.summary()
print(summary["run_count"])  # 0
```

## Full Example

```python
import asyncio
from openclaw_sdk import OpenClawClient
from openclaw_sdk.tracking.cost import CostTracker

async def main():
    tracker = CostTracker()

    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agents = ["assistant", "researcher", "coder"]

        for agent_id in agents:
            agent = client.get_agent(agent_id)
            result = await agent.execute("What can you help me with?")
            tracker.record(result)

        # Print per-agent costs
        summary = tracker.summary()
        for agent_id, stats in summary["by_agent"].items():
            print(f"{agent_id}: {stats['total_tokens']} tokens (${stats['cost_usd']:.4f})")

        print(f"\nTotal: ${summary['total_cost_usd']:.4f}")

        # Export for records
        tracker.export_json("session_costs.json")

asyncio.run(main())
```

!!! warning "Estimates only"
    Cost estimates are based on the default pricing table and may not reflect
    your actual billing. Always check your provider's dashboard for
    authoritative usage and cost data.

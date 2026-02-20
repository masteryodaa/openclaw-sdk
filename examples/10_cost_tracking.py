# RUN: python examples/10_cost_tracking.py
"""Cost tracking — CostTracker with a custom CostCallbackHandler, CSV export."""

import asyncio
import csv
import os
import tempfile

from openclaw_sdk import OpenClawClient, ClientConfig, EventType
from openclaw_sdk.callbacks.handler import CallbackHandler
from openclaw_sdk.core.types import ExecutionResult, StreamEvent, TokenUsage
from openclaw_sdk.gateway.mock import MockGateway
from openclaw_sdk.tracking.cost import CostTracker


# ---------------------------------------------------------------------------
# Callback handler that records costs automatically
# ---------------------------------------------------------------------------

class CostCallbackHandler(CallbackHandler):
    """Records each execution result into a CostTracker."""

    def __init__(self, tracker: CostTracker, model: str) -> None:
        self.tracker = tracker
        self.model = model
        self._current_query: str = ""

    async def on_execution_start(self, agent_id: str, query: str) -> None:
        self._current_query = query

    async def on_execution_end(self, agent_id: str, result: ExecutionResult) -> None:
        self.tracker.record(
            result,
            agent_id=agent_id,
            model=self.model,
            query=self._current_query,
        )


# ---------------------------------------------------------------------------
# Simulate an execution with known token counts
# ---------------------------------------------------------------------------

async def _run_once(
    mock: MockGateway,
    tracker: CostTracker,
    agent_id: str,
    query: str,
    response_content: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Emit a DONE event, run execute(), then record costs with real token counts."""
    cb = CostCallbackHandler(tracker, model=model)
    client = OpenClawClient(config=ClientConfig(), gateway=mock, callbacks=[cb])

    mock.emit_event(
        StreamEvent(
            event_type=EventType.DONE,
            data={"payload": {"runId": "r1", "content": response_content}},
        )
    )
    agent = client.get_agent(agent_id)
    result = await agent.execute(query)

    # The callback recorded the result with zero tokens (MockGateway does not set
    # token counts). Overwrite the last entry's token values by recording again
    # with the simulated counts.
    result.token_usage = TokenUsage(input=input_tokens, output=output_tokens)
    tracker.record(result, agent_id=agent_id, model=model, query=query)


async def main() -> None:
    tracker = CostTracker()

    mock = MockGateway()
    await mock.connect()
    mock.register("chat.send", {"runId": "r1", "status": "started"})

    # Run three simulated executions with different agents and models
    await _run_once(
        mock, tracker,
        agent_id="analyst", query="Summarise Q4 revenue",
        response_content="Q4 revenue was $2.3M, up 18% YoY.",
        model="claude-sonnet-4-20250514",
        input_tokens=500, output_tokens=150,
    )

    await _run_once(
        mock, tracker,
        agent_id="writer", query="Write executive summary",
        response_content="Here is your executive summary for Q4.",
        model="gpt-4o",
        input_tokens=800, output_tokens=400,
    )

    await _run_once(
        mock, tracker,
        agent_id="reviewer", query="Review the draft",
        response_content="Looks good — minor edits suggested.",
        model="gpt-4o-mini",
        input_tokens=600, output_tokens=120,
    )

    # --- Print summary (filtered to only the manually-recorded entries) ---
    # Each _run_once call records twice: once from the callback (0 tokens) and
    # once manually (real tokens). Get_summary shows all entries.
    summary = tracker.get_summary()
    print("Cost Summary (all entries)")
    print("=" * 40)
    print(f"  Total queries       : {summary.total_queries}")
    print(f"  Total input tokens  : {summary.total_input_tokens:,}")
    print(f"  Total output tokens : {summary.total_output_tokens:,}")
    print(f"  Total cost (USD)    : ${summary.total_cost_usd:.6f}")
    print(f"  Avg cost/query      : ${summary.avg_cost_per_query_usd:.6f}")
    print(f"  Avg latency (ms)    : {summary.avg_latency_ms:.1f}")
    print()
    print("  By agent:")
    for agent_id, cost in summary.by_agent.items():
        print(f"    {agent_id:<20} ${cost:.6f}")
    print()
    print("  By model:")
    for model, cost in summary.by_model.items():
        print(f"    {model:<35} ${cost:.6f}")

    # --- Export to CSV ---
    csv_path = os.path.join(tempfile.gettempdir(), "openclaw_costs.csv")
    await tracker.export_csv(csv_path)
    print(f"\nExported CSV to: {csv_path}")

    # Read back rows to verify
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    print(f"CSV rows written: {len(rows)}")
    if rows:
        first = rows[0]
        print(
            f"  First row — agent={first['agent_id']}, model={first['model']}, "
            f"cost=${float(first['estimated_cost_usd']):.6f}"
        )

    await mock.close()


if __name__ == "__main__":
    asyncio.run(main())

from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from pydantic import BaseModel, Field

from openclaw_sdk.core.types import ExecutionResult, TokenUsage

logger = structlog.get_logger(__name__)

# Approximate pricing in USD per 1 million tokens.
# These values are approximate and subject to change. Override via CostTracker(pricing=...).
DEFAULT_PRICING: dict[str, dict[str, float]] = {
    "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
    "claude-haiku-3": {"input": 0.25, "output": 1.25},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
}


class CostEntry(BaseModel):
    timestamp: datetime
    agent_id: str
    user_id: str | None = None
    query: str
    input_tokens: int
    output_tokens: int
    model: str
    estimated_cost_usd: float
    latency_ms: int


class CostSummary(BaseModel):
    total_cost_usd: float
    total_queries: int
    total_input_tokens: int
    total_output_tokens: int
    avg_cost_per_query_usd: float
    avg_latency_ms: float
    by_agent: dict[str, float] = Field(default_factory=dict)
    by_model: dict[str, float] = Field(default_factory=dict)


class CostTracker:
    """Tracks token usage and estimated costs across agent executions.

    Args:
        pricing: Optional dict mapping model name to {"input": float, "output": float}
                 costs in USD per 1 million tokens. Defaults to DEFAULT_PRICING.
    """

    def __init__(self, pricing: dict[str, dict[str, float]] | None = None) -> None:
        self._pricing: dict[str, dict[str, float]] = pricing if pricing is not None else DEFAULT_PRICING
        self._entries: list[CostEntry] = []

    def _calculate_cost(self, model: str, token_usage: TokenUsage) -> float:
        """Calculate estimated cost in USD for a given model and token usage."""
        if model not in self._pricing:
            logger.warning("model_not_in_pricing", model=model)
            return 0.0
        rates = self._pricing[model]
        input_cost = (token_usage.input / 1_000_000) * rates["input"]
        output_cost = (token_usage.output / 1_000_000) * rates["output"]
        return input_cost + output_cost

    def record(
        self,
        result: ExecutionResult,
        agent_id: str,
        model: str,
        query: str = "",
        user_id: str | None = None,
    ) -> CostEntry:
        """Record an execution result and return the resulting CostEntry.

        Calculates cost from result.token_usage using the pricing table.
        If the model is not in the pricing table, cost is recorded as 0.0.
        """
        estimated_cost = self._calculate_cost(model, result.token_usage)
        entry = CostEntry(
            timestamp=datetime.now(timezone.utc),
            agent_id=agent_id,
            user_id=user_id,
            query=query,
            input_tokens=result.token_usage.input,
            output_tokens=result.token_usage.output,
            model=model,
            estimated_cost_usd=estimated_cost,
            latency_ms=result.latency_ms,
        )
        self._entries.append(entry)
        return entry

    def get_summary(
        self,
        agent_id: str | None = None,
        user_id: str | None = None,
        since: datetime | None = None,
    ) -> CostSummary:
        """Return aggregated cost statistics, optionally filtered.

        Args:
            agent_id: If provided, only include entries for this agent.
            user_id: If provided, only include entries for this user.
            since: If provided, only include entries at or after this timestamp.
        """
        entries = self._entries

        if agent_id is not None:
            entries = [e for e in entries if e.agent_id == agent_id]
        if user_id is not None:
            entries = [e for e in entries if e.user_id == user_id]
        if since is not None:
            entries = [e for e in entries if e.timestamp >= since]

        total_queries = len(entries)
        total_cost = sum(e.estimated_cost_usd for e in entries)
        total_input = sum(e.input_tokens for e in entries)
        total_output = sum(e.output_tokens for e in entries)
        avg_cost = total_cost / total_queries if total_queries > 0 else 0.0
        avg_latency = sum(e.latency_ms for e in entries) / total_queries if total_queries > 0 else 0.0

        by_agent: dict[str, float] = {}
        for entry in entries:
            by_agent[entry.agent_id] = by_agent.get(entry.agent_id, 0.0) + entry.estimated_cost_usd

        by_model: dict[str, float] = {}
        for entry in entries:
            by_model[entry.model] = by_model.get(entry.model, 0.0) + entry.estimated_cost_usd

        return CostSummary(
            total_cost_usd=total_cost,
            total_queries=total_queries,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            avg_cost_per_query_usd=avg_cost,
            avg_latency_ms=avg_latency,
            by_agent=by_agent,
            by_model=by_model,
        )

    def get_daily_costs(self, days: int = 30) -> dict[str, float]:
        """Return a dict of {date_str: total_cost_usd} for the last N days.

        date_str format is "YYYY-MM-DD". Days with no entries are omitted.
        """
        result: dict[str, float] = {}
        now = datetime.now(timezone.utc)

        # Determine the cutoff date
        cutoff = now - timedelta(days=days)

        for entry in self._entries:
            if entry.timestamp < cutoff:
                continue
            date_str = entry.timestamp.strftime("%Y-%m-%d")
            result[date_str] = result.get(date_str, 0.0) + entry.estimated_cost_usd

        return result

    async def export_csv(self, path: str) -> None:
        """Write all CostEntry records to a CSV file at the given path."""
        fieldnames = [
            "timestamp",
            "agent_id",
            "user_id",
            "query",
            "input_tokens",
            "output_tokens",
            "model",
            "estimated_cost_usd",
            "latency_ms",
        ]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for entry in self._entries:
                writer.writerow({
                    "timestamp": entry.timestamp.isoformat(),
                    "agent_id": entry.agent_id,
                    "user_id": entry.user_id if entry.user_id is not None else "",
                    "query": entry.query,
                    "input_tokens": entry.input_tokens,
                    "output_tokens": entry.output_tokens,
                    "model": entry.model,
                    "estimated_cost_usd": entry.estimated_cost_usd,
                    "latency_ms": entry.latency_ms,
                })

    async def export_json(self, path: str) -> None:
        """Write all CostEntry records to a JSON file at the given path."""
        data: list[dict[str, Any]] = []
        for entry in self._entries:
            d = entry.model_dump()
            # Convert datetime to ISO string for JSON serialisation
            d["timestamp"] = entry.timestamp.isoformat()
            data.append(d)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

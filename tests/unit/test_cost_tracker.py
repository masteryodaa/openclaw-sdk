"""Tests for tracking/cost.py."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from openclaw_sdk.core.types import ExecutionResult, TokenUsage
from openclaw_sdk.tracking.cost import (
    CostEntry,
    CostTracker,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    input_tokens: int = 1000,
    output_tokens: int = 500,
    latency_ms: int = 250,
    success: bool = True,
) -> ExecutionResult:
    return ExecutionResult(
        success=success,
        content="response",
        latency_ms=latency_ms,
        token_usage=TokenUsage(input=input_tokens, output=output_tokens),
    )


MODEL = "claude-sonnet-4-20250514"


# ---------------------------------------------------------------------------
# record() — cost calculation
# ---------------------------------------------------------------------------


def test_record_returns_cost_entry() -> None:
    tracker = CostTracker()
    result = _make_result()
    entry = tracker.record(result, agent_id="a1", model=MODEL, query="hello")
    assert isinstance(entry, CostEntry)
    assert entry.agent_id == "a1"
    assert entry.model == MODEL
    assert entry.query == "hello"
    assert entry.input_tokens == 1000
    assert entry.output_tokens == 500
    assert entry.latency_ms == 250


def test_record_calculates_cost_correctly() -> None:
    """1 000 input + 500 output tokens with sonnet pricing."""
    tracker = CostTracker()
    result = _make_result(input_tokens=1_000_000, output_tokens=1_000_000)
    entry = tracker.record(result, agent_id="a1", model=MODEL)
    # 1M input @ $3.0 + 1M output @ $15.0 = $18.0
    assert abs(entry.estimated_cost_usd - 18.0) < 1e-9


def test_record_fractional_cost() -> None:
    tracker = CostTracker()
    result = _make_result(input_tokens=500_000, output_tokens=250_000)
    entry = tracker.record(result, agent_id="a1", model=MODEL)
    # 0.5M input @ $3.0 = $1.50; 0.25M output @ $15.0 = $3.75; total $5.25
    assert abs(entry.estimated_cost_usd - 5.25) < 1e-9


def test_record_unknown_model_returns_zero_cost() -> None:
    """Unknown model should record 0 cost without raising."""
    tracker = CostTracker()
    result = _make_result()
    entry = tracker.record(result, agent_id="a1", model="some-unknown-model-x")
    assert entry.estimated_cost_usd == 0.0


def test_record_stores_user_id() -> None:
    tracker = CostTracker()
    entry = tracker.record(_make_result(), agent_id="a1", model=MODEL, user_id="user42")
    assert entry.user_id == "user42"


def test_record_custom_pricing() -> None:
    custom = {"my-model": {"input": 1.0, "output": 2.0}}
    tracker = CostTracker(pricing=custom)
    result = _make_result(input_tokens=1_000_000, output_tokens=1_000_000)
    entry = tracker.record(result, agent_id="a1", model="my-model")
    assert abs(entry.estimated_cost_usd - 3.0) < 1e-9


# ---------------------------------------------------------------------------
# get_summary() — aggregation and filtering
# ---------------------------------------------------------------------------


def test_get_summary_empty() -> None:
    tracker = CostTracker()
    summary = tracker.get_summary()
    assert summary.total_queries == 0
    assert summary.total_cost_usd == 0.0
    assert summary.avg_cost_per_query_usd == 0.0
    assert summary.avg_latency_ms == 0.0


def test_get_summary_totals() -> None:
    tracker = CostTracker()
    tracker.record(_make_result(input_tokens=1_000_000, output_tokens=0, latency_ms=100), "a1", MODEL)
    tracker.record(_make_result(input_tokens=0, output_tokens=1_000_000, latency_ms=200), "a1", MODEL)
    summary = tracker.get_summary()
    assert summary.total_queries == 2
    # 1M input @ $3 = $3; 1M output @ $15 = $15; total $18
    assert abs(summary.total_cost_usd - 18.0) < 1e-9
    assert abs(summary.avg_latency_ms - 150.0) < 1e-9


def test_get_summary_filter_by_agent_id() -> None:
    tracker = CostTracker()
    tracker.record(_make_result(), "agent_a", MODEL, query="q1")
    tracker.record(_make_result(), "agent_b", MODEL, query="q2")
    summary = tracker.get_summary(agent_id="agent_a")
    assert summary.total_queries == 1
    assert "agent_b" not in summary.by_agent


def test_get_summary_filter_by_user_id() -> None:
    tracker = CostTracker()
    tracker.record(_make_result(), "a1", MODEL, user_id="user1")
    tracker.record(_make_result(), "a1", MODEL, user_id="user2")
    summary = tracker.get_summary(user_id="user1")
    assert summary.total_queries == 1


def test_get_summary_filter_by_since() -> None:
    tracker = CostTracker()
    # Record an entry, then manipulate timestamp via internal list
    tracker.record(_make_result(), "a1", MODEL)
    tracker.record(_make_result(), "a1", MODEL)

    # Backdate the first entry
    old_ts = datetime.now(timezone.utc) - timedelta(days=10)
    tracker._entries[0] = tracker._entries[0].model_copy(update={"timestamp": old_ts})

    cutoff = datetime.now(timezone.utc) - timedelta(days=1)
    summary = tracker.get_summary(since=cutoff)
    assert summary.total_queries == 1


def test_get_summary_by_agent_breakdown() -> None:
    tracker = CostTracker()
    tracker.record(_make_result(input_tokens=1_000_000, output_tokens=0), "agent_a", MODEL)
    tracker.record(_make_result(input_tokens=1_000_000, output_tokens=0), "agent_b", MODEL)
    summary = tracker.get_summary()
    assert "agent_a" in summary.by_agent
    assert "agent_b" in summary.by_agent
    # Each: 1M input @ $3 = $3
    assert abs(summary.by_agent["agent_a"] - 3.0) < 1e-9


def test_get_summary_by_model_breakdown() -> None:
    tracker = CostTracker()
    tracker.record(_make_result(input_tokens=1_000_000, output_tokens=0), "a1", MODEL)
    tracker.record(_make_result(input_tokens=1_000_000, output_tokens=0), "a1", "gpt-4o")
    summary = tracker.get_summary()
    assert MODEL in summary.by_model
    assert "gpt-4o" in summary.by_model


# ---------------------------------------------------------------------------
# get_daily_costs()
# ---------------------------------------------------------------------------


def test_get_daily_costs_empty() -> None:
    tracker = CostTracker()
    result = tracker.get_daily_costs(days=7)
    assert result == {}


def test_get_daily_costs_groups_by_day() -> None:
    tracker = CostTracker()
    tracker.record(_make_result(input_tokens=1_000_000, output_tokens=0), "a1", MODEL)
    tracker.record(_make_result(input_tokens=1_000_000, output_tokens=0), "a1", MODEL)
    daily = tracker.get_daily_costs(days=1)
    assert len(daily) == 1  # both on today
    date_key = list(daily.keys())[0]
    # 2 × ($3) = $6
    assert abs(daily[date_key] - 6.0) < 1e-9


def test_get_daily_costs_excludes_old_entries() -> None:
    tracker = CostTracker()
    tracker.record(_make_result(input_tokens=1_000_000, output_tokens=0), "a1", MODEL)
    # Backdate the entry beyond the window
    old_ts = datetime.now(timezone.utc) - timedelta(days=40)
    tracker._entries[0] = tracker._entries[0].model_copy(update={"timestamp": old_ts})

    daily = tracker.get_daily_costs(days=30)
    assert daily == {}


def test_get_daily_costs_multiple_days() -> None:
    tracker = CostTracker()
    tracker.record(_make_result(input_tokens=1_000_000, output_tokens=0), "a1", MODEL)
    tracker.record(_make_result(input_tokens=1_000_000, output_tokens=0), "a1", MODEL)
    # Move first entry to yesterday
    yesterday_ts = datetime.now(timezone.utc) - timedelta(days=1)
    tracker._entries[0] = tracker._entries[0].model_copy(update={"timestamp": yesterday_ts})

    daily = tracker.get_daily_costs(days=7)
    assert len(daily) == 2


# ---------------------------------------------------------------------------
# export_csv()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_csv_creates_file(tmp_path: Path) -> None:
    tracker = CostTracker()
    tracker.record(_make_result(), "a1", MODEL, query="test query", user_id="u1")
    path = str(tmp_path / "costs.csv")
    await tracker.export_csv(path)
    assert (tmp_path / "costs.csv").exists()


@pytest.mark.asyncio
async def test_export_csv_valid_content(tmp_path: Path) -> None:
    tracker = CostTracker()
    tracker.record(_make_result(input_tokens=100, output_tokens=50), "a1", MODEL, query="hi")
    path = str(tmp_path / "costs.csv")
    await tracker.export_csv(path)

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 1
    row = rows[0]
    assert row["agent_id"] == "a1"
    assert row["model"] == MODEL
    assert row["query"] == "hi"
    assert int(row["input_tokens"]) == 100
    assert int(row["output_tokens"]) == 50


@pytest.mark.asyncio
async def test_export_csv_header_row(tmp_path: Path) -> None:
    tracker = CostTracker()
    path = str(tmp_path / "empty.csv")
    await tracker.export_csv(path)

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)

    assert "agent_id" in header
    assert "estimated_cost_usd" in header
    assert "timestamp" in header


# ---------------------------------------------------------------------------
# export_json()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_json_creates_file(tmp_path: Path) -> None:
    tracker = CostTracker()
    tracker.record(_make_result(), "a1", MODEL)
    path = str(tmp_path / "costs.json")
    await tracker.export_json(path)
    assert (tmp_path / "costs.json").exists()


@pytest.mark.asyncio
async def test_export_json_valid_content(tmp_path: Path) -> None:
    tracker = CostTracker()
    tracker.record(_make_result(input_tokens=200, output_tokens=100), "a1", MODEL, query="q1")
    path = str(tmp_path / "costs.json")
    await tracker.export_json(path)

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, list)
    assert len(data) == 1
    entry = data[0]
    assert entry["agent_id"] == "a1"
    assert entry["input_tokens"] == 200
    assert entry["output_tokens"] == 100
    assert "timestamp" in entry


@pytest.mark.asyncio
async def test_export_json_empty(tmp_path: Path) -> None:
    tracker = CostTracker()
    path = str(tmp_path / "empty.json")
    await tracker.export_json(path)

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    assert data == []

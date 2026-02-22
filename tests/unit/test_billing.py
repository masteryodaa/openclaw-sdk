"""Tests for billing/ — models and BillingManager."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest

from openclaw_sdk.billing.engine import BillingManager
from openclaw_sdk.billing.models import (
    BillingPeriod,
    Invoice,
    LineItem,
    PricingTier,
    UsageRecord,
)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------


def test_pricing_tier_defaults() -> None:
    tier = PricingTier(name="free")
    assert tier.input_price_per_million == 0.0
    assert tier.included_queries == 0


def test_usage_record_defaults() -> None:
    rec = UsageRecord(tenant_id="t1", agent_id="a1")
    assert rec.input_tokens == 0
    assert rec.cost_usd == 0.0
    assert rec.timestamp.tzinfo is not None


def test_billing_period_properties() -> None:
    now = datetime.now(timezone.utc)
    period = BillingPeriod(
        start=now - timedelta(days=30),
        end=now,
        tenant_id="t1",
        records=[
            UsageRecord(tenant_id="t1", agent_id="a1", cost_usd=0.5),
            UsageRecord(tenant_id="t1", agent_id="a1", cost_usd=1.5),
        ],
    )
    assert period.total_cost == 2.0
    assert period.total_queries == 2


def test_invoice_defaults() -> None:
    now = datetime.now(timezone.utc)
    inv = Invoice(
        tenant_id="t1",
        period_start=now - timedelta(days=30),
        period_end=now,
    )
    assert len(inv.invoice_id) == 12
    assert inv.currency == "USD"
    assert inv.status == "draft"
    assert inv.line_items == []


def test_line_item() -> None:
    li = LineItem(description="Tokens", quantity=1000.0, unit_price=0.003, total=3.0)
    assert li.total == 3.0


# ---------------------------------------------------------------------------
# BillingManager — set_pricing and record_usage
# ---------------------------------------------------------------------------


def test_set_pricing_and_record() -> None:
    mgr = BillingManager()
    tier = PricingTier(name="pro", input_price_per_million=3.0, output_price_per_million=15.0)
    mgr.set_pricing("t1", tier)

    rec = UsageRecord(tenant_id="t1", agent_id="a1", input_tokens=1000, output_tokens=500)
    mgr.record_usage(rec)

    summary = mgr.get_usage_summary("t1")
    assert summary["total_queries"] == 1
    assert summary["total_input_tokens"] == 1000
    assert summary["total_output_tokens"] == 500


# ---------------------------------------------------------------------------
# generate_invoice — with pricing tier
# ---------------------------------------------------------------------------


def test_generate_invoice_with_tier() -> None:
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=30)

    tier = PricingTier(
        name="pro",
        input_price_per_million=3.0,
        output_price_per_million=15.0,
        included_queries=1,
        overage_price_per_query=0.01,
    )
    mgr = BillingManager(pricing={"t1": tier})

    # Add 3 usage records.
    for _ in range(3):
        mgr.record_usage(
            UsageRecord(
                tenant_id="t1",
                agent_id="a1",
                input_tokens=1_000_000,
                output_tokens=500_000,
                timestamp=now - timedelta(days=1),
            )
        )

    invoice = mgr.generate_invoice("t1", start, now)
    assert invoice.tenant_id == "t1"
    assert len(invoice.line_items) == 3  # input + output + overage

    # Input: 3M tokens * $3/M = $9.
    input_li = invoice.line_items[0]
    assert input_li.total == 9.0

    # Output: 1.5M tokens * $15/M = $22.5.
    output_li = invoice.line_items[1]
    assert output_li.total == 22.5

    # Overage: 3 queries - 1 included = 2 overage * $0.01 = $0.02.
    overage_li = invoice.line_items[2]
    assert overage_li.total == 0.02

    assert invoice.subtotal == pytest.approx(31.52)
    assert invoice.total == invoice.subtotal


def test_generate_invoice_without_tier() -> None:
    """Without a pricing tier, invoice sums raw cost_usd from records."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=30)
    mgr = BillingManager()

    mgr.record_usage(
        UsageRecord(
            tenant_id="t1",
            agent_id="a1",
            cost_usd=0.05,
            timestamp=now - timedelta(days=1),
        )
    )

    invoice = mgr.generate_invoice("t1", start, now)
    assert len(invoice.line_items) == 1
    assert invoice.subtotal == pytest.approx(0.05)


def test_generate_invoice_empty_period() -> None:
    now = datetime.now(timezone.utc)
    mgr = BillingManager()
    invoice = mgr.generate_invoice("t1", now - timedelta(days=30), now)
    assert invoice.line_items == []
    assert invoice.subtotal == 0.0


# ---------------------------------------------------------------------------
# get_usage_summary — filtering by since
# ---------------------------------------------------------------------------


def test_usage_summary_since_filter() -> None:
    now = datetime.now(timezone.utc)
    mgr = BillingManager()

    old = UsageRecord(
        tenant_id="t1",
        agent_id="a1",
        cost_usd=1.0,
        timestamp=now - timedelta(days=60),
    )
    recent = UsageRecord(
        tenant_id="t1",
        agent_id="a1",
        cost_usd=2.0,
        timestamp=now - timedelta(days=1),
    )
    mgr.record_usage(old)
    mgr.record_usage(recent)

    summary = mgr.get_usage_summary("t1", since=now - timedelta(days=30))
    assert summary["total_queries"] == 1
    assert summary["total_cost_usd"] == pytest.approx(2.0)


def test_usage_summary_empty() -> None:
    mgr = BillingManager()
    summary = mgr.get_usage_summary("nonexistent")
    assert summary["total_queries"] == 0
    assert summary["total_cost_usd"] == 0.0


# ---------------------------------------------------------------------------
# export_invoice_json
# ---------------------------------------------------------------------------


async def test_export_invoice_json(tmp_path: object) -> None:
    now = datetime.now(timezone.utc)
    invoice = Invoice(
        tenant_id="t1",
        period_start=now - timedelta(days=30),
        period_end=now,
        subtotal=5.0,
        total=5.0,
    )
    mgr = BillingManager()
    out_path = tmp_path / "invoice.json"  # type: ignore[operator]
    await mgr.export_invoice_json(invoice, out_path)

    data = json.loads(out_path.read_text(encoding="utf-8"))  # type: ignore[union-attr]
    assert data["tenant_id"] == "t1"
    assert data["total"] == 5.0

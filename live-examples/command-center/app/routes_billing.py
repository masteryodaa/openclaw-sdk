"""Billing endpoints — pricing tiers, usage tracking, and invoice generation."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from openclaw_sdk.billing import BillingManager, PricingTier, UsageRecord

from . import gateway

router = APIRouter(prefix="/api/billing", tags=["billing"])

# Shared singleton instance (per-server lifetime)
_billing = BillingManager()

# Keep track of invoices for listing
_invoices: list[dict] = []


# -- Request models --


class AddTierBody(BaseModel):
    tenant_id: str
    name: str
    input_price_per_million: float = 0.0
    output_price_per_million: float = 0.0
    included_queries: int = 0
    overage_price_per_query: float = 0.0


class RecordUsageBody(BaseModel):
    tenant_id: str
    agent_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    cost_usd: float = 0.0


class GenerateInvoiceBody(BaseModel):
    tenant_id: str
    period_start: str  # ISO datetime
    period_end: str  # ISO datetime


# -- Endpoints --


@router.post("/tiers")
async def add_tier(body: AddTierBody):
    """Add or update a pricing tier for a tenant."""
    tier = PricingTier(
        name=body.name,
        input_price_per_million=body.input_price_per_million,
        output_price_per_million=body.output_price_per_million,
        included_queries=body.included_queries,
        overage_price_per_query=body.overage_price_per_query,
    )
    _billing.set_pricing(body.tenant_id, tier)
    return {
        "tenant_id": body.tenant_id,
        "tier": body.name,
        "set": True,
    }


@router.get("/tiers")
async def list_tiers():
    """List all configured pricing tiers."""
    tiers = []
    for tenant_id, tier in _billing._pricing.items():
        tiers.append({
            "tenant_id": tenant_id,
            "name": tier.name,
            "input_price_per_million": tier.input_price_per_million,
            "output_price_per_million": tier.output_price_per_million,
            "included_queries": tier.included_queries,
            "overage_price_per_query": tier.overage_price_per_query,
        })
    return {"tiers": tiers}


@router.post("/usage")
async def record_usage(body: RecordUsageBody):
    """Record a usage event for billing."""
    record = UsageRecord(
        tenant_id=body.tenant_id,
        agent_id=body.agent_id,
        input_tokens=body.input_tokens,
        output_tokens=body.output_tokens,
        model=body.model,
        cost_usd=body.cost_usd,
    )
    _billing.record_usage(record)
    return {
        "recorded": True,
        "tenant_id": body.tenant_id,
        "timestamp": record.timestamp.isoformat(),
    }


@router.get("/usage/{tenant_id}")
async def get_usage(tenant_id: str):
    """Get aggregated usage summary for a tenant."""
    summary = _billing.get_usage_summary(tenant_id)
    return summary


@router.post("/invoices")
async def generate_invoice(body: GenerateInvoiceBody):
    """Generate an invoice for a tenant over a billing period."""
    period_start = datetime.fromisoformat(body.period_start)
    period_end = datetime.fromisoformat(body.period_end)
    # Ensure timezone-aware to match UsageRecord.timestamp (UTC)
    if period_start.tzinfo is None:
        period_start = period_start.replace(tzinfo=timezone.utc)
    if period_end.tzinfo is None:
        period_end = period_end.replace(tzinfo=timezone.utc)
    invoice = _billing.generate_invoice(body.tenant_id, period_start, period_end)
    invoice_data = {
        "invoice_id": invoice.invoice_id,
        "tenant_id": invoice.tenant_id,
        "period_start": invoice.period_start.isoformat(),
        "period_end": invoice.period_end.isoformat(),
        "line_items": [
            {
                "description": li.description,
                "quantity": li.quantity,
                "unit_price": li.unit_price,
                "total": li.total,
            }
            for li in invoice.line_items
        ],
        "subtotal": invoice.subtotal,
        "total": invoice.total,
        "currency": invoice.currency,
        "status": invoice.status,
        "created_at": invoice.created_at.isoformat(),
    }
    _invoices.append(invoice_data)
    return invoice_data


@router.get("/invoices")
async def list_invoices():
    """List all generated invoices."""
    return {"invoices": _invoices}

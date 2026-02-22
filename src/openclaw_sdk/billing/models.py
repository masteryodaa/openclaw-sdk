"""Billing data models — pricing tiers, usage records, invoices."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field


class PricingTier(BaseModel):
    """Token-based pricing configuration for a tenant.

    Pricing is expressed in USD per million tokens, plus an optional
    per-query overage charge after a free-tier allowance.
    """

    name: str
    input_price_per_million: float = 0.0
    output_price_per_million: float = 0.0
    included_queries: int = 0
    overage_price_per_query: float = 0.0


class UsageRecord(BaseModel):
    """A single usage event tied to a tenant and agent."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tenant_id: str
    agent_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    cost_usd: float = 0.0


class BillingPeriod(BaseModel):
    """Aggregated usage for a tenant over a time range."""

    start: datetime
    end: datetime
    tenant_id: str
    records: list[UsageRecord] = Field(default_factory=list)

    @property
    def total_cost(self) -> float:
        """Sum of ``cost_usd`` across all records."""
        return sum(r.cost_usd for r in self.records)

    @property
    def total_queries(self) -> int:
        """Number of usage records in the period."""
        return len(self.records)


class LineItem(BaseModel):
    """A single line on an invoice."""

    description: str
    quantity: float
    unit_price: float
    total: float


class Invoice(BaseModel):
    """A generated invoice for a tenant's billing period."""

    invoice_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    tenant_id: str
    period_start: datetime
    period_end: datetime
    line_items: list[LineItem] = Field(default_factory=list)
    subtotal: float = 0.0
    tax_rate: float = 0.0
    total: float = 0.0
    currency: str = "USD"
    status: str = "draft"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

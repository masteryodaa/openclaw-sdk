"""Billing engine — usage tracking, invoice generation, and export."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from openclaw_sdk.billing.models import (
    Invoice,
    LineItem,
    PricingTier,
    UsageRecord,
)

logger = structlog.get_logger(__name__)


class BillingManager:
    """Tracks per-tenant token usage and generates invoices.

    Args:
        pricing: Optional mapping of ``tenant_id`` to :class:`PricingTier`.
    """

    def __init__(self, pricing: dict[str, PricingTier] | None = None) -> None:
        self._pricing: dict[str, PricingTier] = dict(pricing) if pricing else {}
        self._records: list[UsageRecord] = []

    def set_pricing(self, tenant_id: str, tier: PricingTier) -> None:
        """Configure or update the pricing tier for a tenant."""
        self._pricing[tenant_id] = tier
        logger.info("billing_pricing_set", tenant_id=tenant_id, tier=tier.name)

    def record_usage(self, record: UsageRecord) -> None:
        """Append a usage record."""
        self._records.append(record)

    def _period_records(
        self,
        tenant_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> list[UsageRecord]:
        """Filter records for a tenant within a billing period."""
        return [
            r
            for r in self._records
            if r.tenant_id == tenant_id
            and r.timestamp >= period_start
            and r.timestamp < period_end
        ]

    def generate_invoice(
        self,
        tenant_id: str,
        period_start: datetime,
        period_end: datetime,
    ) -> Invoice:
        """Generate an invoice for a tenant over the specified period.

        Line items are computed from the tenant's :class:`PricingTier`
        (if configured) and the raw usage records.
        """
        records = self._period_records(tenant_id, period_start, period_end)
        tier = self._pricing.get(tenant_id)

        total_input = sum(r.input_tokens for r in records)
        total_output = sum(r.output_tokens for r in records)
        query_count = len(records)

        line_items: list[LineItem] = []

        if tier is not None:
            # Token-based charges.
            if total_input > 0:
                input_cost = (total_input / 1_000_000) * tier.input_price_per_million
                line_items.append(
                    LineItem(
                        description=f"Input tokens ({tier.name})",
                        quantity=total_input,
                        unit_price=tier.input_price_per_million / 1_000_000,
                        total=round(input_cost, 6),
                    )
                )

            if total_output > 0:
                output_cost = (total_output / 1_000_000) * tier.output_price_per_million
                line_items.append(
                    LineItem(
                        description=f"Output tokens ({tier.name})",
                        quantity=total_output,
                        unit_price=tier.output_price_per_million / 1_000_000,
                        total=round(output_cost, 6),
                    )
                )

            # Overage charges.
            overage = max(0, query_count - tier.included_queries)
            if overage > 0 and tier.overage_price_per_query > 0:
                overage_cost = overage * tier.overage_price_per_query
                line_items.append(
                    LineItem(
                        description=f"Overage queries ({overage} beyond {tier.included_queries})",
                        quantity=overage,
                        unit_price=tier.overage_price_per_query,
                        total=round(overage_cost, 6),
                    )
                )
        else:
            # No tier — just sum raw cost_usd from records.
            raw_total = sum(r.cost_usd for r in records)
            if raw_total > 0:
                line_items.append(
                    LineItem(
                        description="Usage charges",
                        quantity=query_count,
                        unit_price=round(raw_total / query_count, 6) if query_count else 0.0,
                        total=round(raw_total, 6),
                    )
                )

        subtotal = round(sum(li.total for li in line_items), 6)

        invoice = Invoice(
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            line_items=line_items,
            subtotal=subtotal,
            total=subtotal,
        )

        logger.info(
            "billing_invoice_generated",
            tenant_id=tenant_id,
            invoice_id=invoice.invoice_id,
            total=invoice.total,
        )
        return invoice

    def get_usage_summary(
        self,
        tenant_id: str,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        """Return an aggregated usage summary for a tenant.

        Returns a dict with ``tenant_id``, ``total_queries``,
        ``total_input_tokens``, ``total_output_tokens``, and
        ``total_cost_usd``.
        """
        filtered = [
            r
            for r in self._records
            if r.tenant_id == tenant_id and (since is None or r.timestamp >= since)
        ]
        return {
            "tenant_id": tenant_id,
            "total_queries": len(filtered),
            "total_input_tokens": sum(r.input_tokens for r in filtered),
            "total_output_tokens": sum(r.output_tokens for r in filtered),
            "total_cost_usd": round(sum(r.cost_usd for r in filtered), 6),
        }

    async def export_invoice_json(self, invoice: Invoice, path: str | Path) -> None:
        """Export an invoice to a JSON file using :func:`asyncio.to_thread`."""
        dest = Path(path)
        data = invoice.model_dump(mode="json")
        payload = json.dumps(data, indent=2, default=str, sort_keys=True)

        def _write() -> None:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(payload, encoding="utf-8")

        await asyncio.to_thread(_write)
        logger.info("billing_invoice_exported", path=str(dest))

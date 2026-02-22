"""Billing endpoints — usage summary and invoice generation."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=["billing"])


@router.get("/api/billing/usage")
async def billing_usage(
    request: Request,
    tenant_id: str = Query(...),
) -> JSONResponse:
    """Get usage summary for a tenant."""
    bm = request.app.state.billing_manager
    if bm is None:
        raise HTTPException(status_code=404, detail="BillingManager not configured")
    summary = bm.get_usage_summary(tenant_id)
    return JSONResponse(content=summary)


@router.get("/api/billing/invoice/{tenant_id}")
async def generate_invoice(
    tenant_id: str,
    request: Request,
    period_start: str | None = Query(default=None),
    period_end: str | None = Query(default=None),
) -> JSONResponse:
    """Generate an invoice for a tenant over a billing period.

    ``period_start`` and ``period_end`` should be ISO-8601 date strings.
    If omitted, defaults to a wide range covering all records.
    """
    bm = request.app.state.billing_manager
    if bm is None:
        raise HTTPException(status_code=404, detail="BillingManager not configured")

    start = (
        datetime.fromisoformat(period_start) if period_start
        else datetime(2000, 1, 1, tzinfo=timezone.utc)
    )
    end = (
        datetime.fromisoformat(period_end) if period_end
        else datetime.now(timezone.utc)
    )

    invoice = bm.generate_invoice(tenant_id, start, end)
    return JSONResponse(content=invoice.model_dump(mode="json"))

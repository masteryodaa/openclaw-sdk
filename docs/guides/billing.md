# Billing

The OpenClaw SDK includes a per-tenant billing system for tracking token usage,
applying pricing tiers, and generating invoices. `BillingManager` records
individual usage events, computes charges based on configurable pricing tiers
(input/output token rates plus overage fees), and exports invoices as JSON.

## Quick Start

```python
import asyncio
from datetime import datetime, timezone, timedelta

from openclaw_sdk.billing import (
    BillingManager,
    PricingTier,
    UsageRecord,
)


async def main():
    # Define a pricing tier
    tier = PricingTier(
        name="standard",
        input_price_per_million=3.0,     # $3.00 per 1M input tokens
        output_price_per_million=15.0,   # $15.00 per 1M output tokens
        included_queries=1000,           # First 1000 queries free
        overage_price_per_query=0.01,    # $0.01 per query beyond 1000
    )

    # Set up billing
    billing = BillingManager()
    billing.set_pricing("tenant-acme", tier)

    # Record usage events
    billing.record_usage(UsageRecord(
        tenant_id="tenant-acme",
        agent_id="assistant",
        input_tokens=2500,
        output_tokens=800,
        model="claude-sonnet-4-20250514",
    ))

    billing.record_usage(UsageRecord(
        tenant_id="tenant-acme",
        agent_id="assistant",
        input_tokens=1800,
        output_tokens=600,
        model="claude-sonnet-4-20250514",
    ))

    # Generate an invoice
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=30)
    invoice = billing.generate_invoice("tenant-acme", period_start, now)

    print(f"Invoice {invoice.invoice_id}: ${invoice.total:.4f}")
    for item in invoice.line_items:
        print(f"  {item.description}: ${item.total:.6f}")

    # Export to JSON
    await billing.export_invoice_json(invoice, "invoices/acme-feb.json")

asyncio.run(main())
```

## PricingTier

`PricingTier` defines the billing rates for a tenant. It supports token-based
pricing with separate input/output rates, a free-tier query allowance, and
per-query overage charges.

```python
from openclaw_sdk.billing import PricingTier

# Enterprise tier with generous free allowance
enterprise = PricingTier(
    name="enterprise",
    input_price_per_million=2.5,
    output_price_per_million=10.0,
    included_queries=10000,
    overage_price_per_query=0.005,
)

# Pay-as-you-go tier with no free queries
paygo = PricingTier(
    name="pay-as-you-go",
    input_price_per_million=5.0,
    output_price_per_million=20.0,
    included_queries=0,
    overage_price_per_query=0.02,
)
```

| Field                      | Type    | Default | Description                               |
|----------------------------|---------|---------|-------------------------------------------|
| `name`                     | `str`   | --      | Tier name (e.g. `"standard"`, `"enterprise"`) |
| `input_price_per_million`  | `float` | `0.0`   | USD per million input tokens              |
| `output_price_per_million` | `float` | `0.0`   | USD per million output tokens             |
| `included_queries`         | `int`   | `0`     | Free queries before overage kicks in      |
| `overage_price_per_query`  | `float` | `0.0`   | USD per query beyond the free allowance   |

!!! tip "Different tiers for different tenants"
    Each tenant can have its own pricing tier. Call `billing.set_pricing()` with
    the tenant ID and tier to configure or update pricing at any time.

## UsageRecord

A `UsageRecord` captures a single billable event -- typically one agent
execution.

```python
from openclaw_sdk.billing import UsageRecord

record = UsageRecord(
    tenant_id="tenant-acme",
    agent_id="assistant",
    input_tokens=4200,
    output_tokens=1500,
    model="claude-sonnet-4-20250514",
    cost_usd=0.0,  # Computed by the tier, or pre-calculated
)
```

| Field          | Type       | Default        | Description                             |
|----------------|------------|----------------|-----------------------------------------|
| `timestamp`    | `datetime` | Now (UTC)      | When the usage occurred                 |
| `tenant_id`    | `str`      | --             | Tenant that incurred the usage          |
| `agent_id`     | `str`      | --             | Agent that performed the execution      |
| `input_tokens` | `int`      | `0`            | Number of input tokens consumed         |
| `output_tokens`| `int`      | `0`            | Number of output tokens generated       |
| `model`        | `str`      | `""`           | Model identifier (for reporting)        |
| `cost_usd`     | `float`    | `0.0`          | Pre-calculated cost (used when no tier) |

## BillingPeriod

`BillingPeriod` aggregates usage records for a tenant over a time range. It is
primarily a reporting model with convenience properties.

```python
from openclaw_sdk.billing import BillingPeriod

period = BillingPeriod(
    start=period_start,
    end=period_end,
    tenant_id="tenant-acme",
    records=filtered_records,
)

print(f"Total cost: ${period.total_cost:.4f}")
print(f"Total queries: {period.total_queries}")
```

| Field       | Type               | Default | Description                               |
|-------------|--------------------|---------|-------------------------------------------|
| `start`     | `datetime`         | --      | Period start (inclusive)                   |
| `end`       | `datetime`         | --      | Period end (exclusive)                     |
| `tenant_id` | `str`              | --      | Tenant ID                                 |
| `records`   | `list[UsageRecord]`| `[]`    | Usage records within the period           |

| Property        | Type    | Description                              |
|-----------------|---------|------------------------------------------|
| `total_cost`    | `float` | Sum of `cost_usd` across all records     |
| `total_queries` | `int`   | Number of records in the period          |

## Invoice and LineItem

`Invoice` is the output of `generate_invoice()`. It contains one or more
`LineItem` entries that break down the charges.

### LineItem

```python
from openclaw_sdk.billing import LineItem

item = LineItem(
    description="Input tokens (standard)",
    quantity=50000,
    unit_price=0.000003,   # $3.00 / 1,000,000
    total=0.15,
)
```

| Field         | Type    | Default | Description                          |
|---------------|---------|---------|--------------------------------------|
| `description` | `str`   | --      | Human-readable charge description    |
| `quantity`    | `float` | --      | Number of units (tokens or queries)  |
| `unit_price`  | `float` | --      | Price per unit                       |
| `total`       | `float` | --      | Line total (`quantity * unit_price`)  |

### Invoice

```python
from openclaw_sdk.billing import Invoice

# Invoices are typically created by BillingManager.generate_invoice()
print(f"Invoice: {invoice.invoice_id}")
print(f"Period: {invoice.period_start} to {invoice.period_end}")
print(f"Subtotal: ${invoice.subtotal:.4f}")
print(f"Total: ${invoice.total:.4f} {invoice.currency}")
print(f"Status: {invoice.status}")
```

| Field          | Type              | Default        | Description                          |
|----------------|-------------------|----------------|--------------------------------------|
| `invoice_id`   | `str`             | Auto-generated | 12-character hex identifier          |
| `tenant_id`    | `str`             | --             | Tenant being billed                  |
| `period_start` | `datetime`        | --             | Billing period start                 |
| `period_end`   | `datetime`        | --             | Billing period end                   |
| `line_items`   | `list[LineItem]`  | `[]`           | Itemised charges                     |
| `subtotal`     | `float`           | `0.0`          | Sum of line item totals              |
| `tax_rate`     | `float`           | `0.0`          | Tax rate (0.0 = no tax)              |
| `total`        | `float`           | `0.0`          | Final total including tax            |
| `currency`     | `str`             | `"USD"`        | Currency code                        |
| `status`       | `str`             | `"draft"`      | Invoice status (e.g. `"draft"`, `"sent"`) |
| `created_at`   | `datetime`        | Now (UTC)      | When the invoice was generated       |

## BillingManager

`BillingManager` is the central engine that ties pricing, usage tracking, and
invoice generation together.

```python
from openclaw_sdk.billing import BillingManager, PricingTier

billing = BillingManager()
```

You can also pass initial pricing at construction time:

```python
billing = BillingManager(pricing={
    "tenant-acme": PricingTier(name="standard", input_price_per_million=3.0, output_price_per_million=15.0),
    "tenant-beta": PricingTier(name="enterprise", input_price_per_million=2.5, output_price_per_million=10.0),
})
```

| Method                                      | Returns          | Description                                |
|---------------------------------------------|------------------|--------------------------------------------|
| `set_pricing(tenant_id, tier)`              | `None`           | Set or update pricing for a tenant         |
| `record_usage(record)`                      | `None`           | Append a usage record                      |
| `generate_invoice(tenant_id, start, end)`   | `Invoice`        | Generate an invoice for a billing period   |
| `get_usage_summary(tenant_id, since=None)`  | `dict[str, Any]` | Aggregated usage summary for a tenant      |
| `export_invoice_json(invoice, path)`        | `None`           | Export invoice to a JSON file (async)      |

### Setting Pricing

```python
billing.set_pricing("tenant-acme", PricingTier(
    name="premium",
    input_price_per_million=2.0,
    output_price_per_million=8.0,
    included_queries=5000,
    overage_price_per_query=0.005,
))
```

### Recording Usage

```python
billing.record_usage(UsageRecord(
    tenant_id="tenant-acme",
    agent_id="assistant",
    input_tokens=3200,
    output_tokens=1100,
    model="claude-sonnet-4-20250514",
))
```

!!! tip "Record after every execution"
    Call `record_usage()` after each `agent.execute()` to ensure accurate
    billing. You can extract token counts from the `ExecutionResult.token_usage`
    field.

### Generating Invoices

The invoice generator computes line items from the tenant's pricing tier:

1. **Input token charges** -- total input tokens multiplied by the per-million rate.
2. **Output token charges** -- total output tokens multiplied by the per-million rate.
3. **Overage charges** -- queries beyond the `included_queries` allowance, charged at `overage_price_per_query`.

If no pricing tier is configured for a tenant, the generator falls back to
summing the raw `cost_usd` from each usage record.

```python
from datetime import datetime, timezone, timedelta

now = datetime.now(timezone.utc)
start = now - timedelta(days=30)

invoice = billing.generate_invoice("tenant-acme", start, now)

print(f"Invoice ID: {invoice.invoice_id}")
print(f"Line items: {len(invoice.line_items)}")
print(f"Total: ${invoice.total:.4f} {invoice.currency}")
```

### Usage Summary

Get an aggregated view of a tenant's usage without generating a full invoice:

```python
summary = billing.get_usage_summary("tenant-acme")
print(summary)
# {
#     "tenant_id": "tenant-acme",
#     "total_queries": 42,
#     "total_input_tokens": 125000,
#     "total_output_tokens": 48000,
#     "total_cost_usd": 0.0
# }

# Filter by time
from datetime import datetime, timezone, timedelta
since = datetime.now(timezone.utc) - timedelta(hours=24)
daily = billing.get_usage_summary("tenant-acme", since=since)
```

| Return Key             | Type    | Description                      |
|------------------------|---------|----------------------------------|
| `tenant_id`            | `str`   | The tenant ID                    |
| `total_queries`        | `int`   | Number of usage records          |
| `total_input_tokens`   | `int`   | Sum of input tokens              |
| `total_output_tokens`  | `int`   | Sum of output tokens             |
| `total_cost_usd`       | `float` | Sum of raw `cost_usd` values     |

### JSON Export

Export an invoice to a JSON file for archival, integration with accounting
systems, or delivery to tenants. File I/O is handled asynchronously via
`asyncio.to_thread`.

```python
await billing.export_invoice_json(invoice, "invoices/acme-2026-02.json")
```

The exported JSON contains the full invoice model with all line items,
timestamps, and metadata. Parent directories are created automatically if they
do not exist.

!!! warning "In-memory storage"
    `BillingManager` stores usage records in memory. Records are lost when the
    process restarts. For production use, persist records to a database and
    load them on startup, or extend `BillingManager` with a storage backend.

## Full Example: Multi-Tenant Billing

```python
import asyncio
from datetime import datetime, timezone, timedelta

from openclaw_sdk import OpenClawClient
from openclaw_sdk.billing import (
    BillingManager,
    PricingTier,
    UsageRecord,
)


async def main():
    # Configure pricing for two tenants
    billing = BillingManager(pricing={
        "acme": PricingTier(
            name="standard",
            input_price_per_million=3.0,
            output_price_per_million=15.0,
            included_queries=500,
            overage_price_per_query=0.01,
        ),
        "globex": PricingTier(
            name="enterprise",
            input_price_per_million=2.0,
            output_price_per_million=10.0,
            included_queries=5000,
            overage_price_per_query=0.005,
        ),
    })

    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        agent = client.get_agent("assistant")

        # Simulate usage for both tenants
        tenants = ["acme", "globex"]
        for tenant in tenants:
            for _ in range(3):
                result = await agent.execute("Hello")
                billing.record_usage(UsageRecord(
                    tenant_id=tenant,
                    agent_id="assistant",
                    input_tokens=result.token_usage.input,
                    output_tokens=result.token_usage.output,
                    model="claude-sonnet-4-20250514",
                ))

    # Generate and export invoices
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=30)

    for tenant in tenants:
        invoice = billing.generate_invoice(tenant, start, now)
        print(f"\n--- {tenant.upper()} ---")
        print(f"Invoice: {invoice.invoice_id}")
        for item in invoice.line_items:
            print(f"  {item.description}: ${item.total:.6f}")
        print(f"  TOTAL: ${invoice.total:.4f} {invoice.currency}")

        await billing.export_invoice_json(
            invoice, f"invoices/{tenant}-{now:%Y-%m}.json"
        )

    # Print usage summaries
    for tenant in tenants:
        summary = billing.get_usage_summary(tenant)
        print(f"\n{tenant}: {summary['total_queries']} queries, "
              f"{summary['total_input_tokens']} input tokens, "
              f"{summary['total_output_tokens']} output tokens")

asyncio.run(main())
```

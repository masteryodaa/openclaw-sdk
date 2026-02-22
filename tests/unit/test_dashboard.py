"""Tests for the dashboard module — FastAPI REST API endpoints.

Uses httpx.ASGITransport + httpx.AsyncClient to test the FastAPI app
with MockGateway providing canned responses.
"""
from __future__ import annotations

from typing import Any

from httpx import ASGITransport, AsyncClient

from openclaw_sdk.audit.logger import AuditLogger
from openclaw_sdk.audit.models import AuditEvent
from openclaw_sdk.audit.sinks import InMemoryAuditSink
from openclaw_sdk.billing.engine import BillingManager
from openclaw_sdk.billing.models import PricingTier, UsageRecord
from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.core.constants import EventType
from openclaw_sdk.core.types import StreamEvent
from openclaw_sdk.dashboard import create_dashboard_app
from openclaw_sdk.gateway.mock import MockGateway
from openclaw_sdk.tracking.cost import CostTracker
from openclaw_sdk.webhooks.manager import WebhookManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_mock_gateway() -> MockGateway:
    """Create a MockGateway with common responses pre-registered."""
    gw = MockGateway()
    gw._connected = True

    # Health already works via MockGateway.health()

    # chat.send → starts a run (agent execution)
    gw.register("chat.send", {"runId": "run-1", "status": "started"})

    # sessions.resolve → agent status
    gw.register("sessions.resolve", {"status": "idle"})

    # sessions.preview
    gw.register("sessions.preview", {"sessions": [{"key": "agent:test:main"}]})

    # sessions.reset
    gw.register("sessions.reset", {"ok": True})

    # sessions.delete
    gw.register("sessions.delete", {"ok": True})

    # config.get
    gw.register("config.get", {
        "path": "/config.json",
        "exists": True,
        "raw": '{"agents": {}}',
        "parsed": {"agents": {}},
    })

    # config.set
    gw.register("config.set", {"ok": True})

    # config.patch
    gw.register("config.patch", {"ok": True})

    # channels.status
    gw.register("channels.status", {
        "channels": {"whatsapp": {"configured": True, "linked": True}},
    })

    # cron.list (for schedules)
    gw.register("cron.list", {"jobs": [
        {"id": "job-1", "name": "daily-check", "schedule": "0 9 * * *",
         "sessionTarget": "agent:main:main", "payload": "hello"},
    ]})

    # cron.remove (for schedule delete)
    gw.register("cron.remove", {"ok": True})

    return gw


def _make_client(gw: MockGateway) -> OpenClawClient:
    """Create an OpenClawClient wired to the mock gateway."""
    config = ClientConfig(mode="local")
    return OpenClawClient(config=config, gateway=gw)


async def _make_app(
    *,
    with_audit: bool = False,
    with_billing: bool = False,
    with_webhooks: bool = False,
    with_cost_tracker: bool = False,
) -> tuple[Any, MockGateway]:
    """Create the dashboard app with optional managers."""
    gw = _make_mock_gateway()
    client = _make_client(gw)

    audit_logger: AuditLogger | None = None
    billing_manager: BillingManager | None = None
    webhook_manager: WebhookManager | None = None
    cost_tracker: CostTracker | None = None

    if with_audit:
        sink = InMemoryAuditSink()
        await sink.write(AuditEvent(
            event_type="execute",
            agent_id="test-agent",
            action="agent.execute",
        ))
        audit_logger = AuditLogger(sinks=[sink])

    if with_billing:
        billing_manager = BillingManager()
        billing_manager.set_pricing("tenant-1", PricingTier(
            name="standard",
            input_price_per_million=3.0,
            output_price_per_million=15.0,
        ))
        billing_manager.record_usage(UsageRecord(
            tenant_id="tenant-1",
            agent_id="test-agent",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.01,
        ))

    if with_webhooks:
        webhook_manager = WebhookManager()

    if with_cost_tracker:
        cost_tracker = CostTracker()

    app = create_dashboard_app(
        client,
        audit_logger=audit_logger,
        billing_manager=billing_manager,
        webhook_manager=webhook_manager,
        cost_tracker=cost_tracker,
    )
    return app, gw


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


async def test_health_endpoint() -> None:
    app, _gw = await _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["healthy"] is True
        assert data["version"] == "mock"


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


async def test_agent_execute() -> None:
    app, gw = await _make_app()
    # Pre-emit events for the execute flow.
    # MockGateway events need data wrapped in {"payload": {...}} to match
    # the event processing in Agent._execute_impl.
    gw.emit_event(StreamEvent(
        event_type=EventType.DONE,
        data={"payload": {"content": "Hello from agent", "stopReason": "complete"}},
    ))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/agents/test-agent/execute",
            json={"query": "Hello"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "Hello from agent" in data["content"]


async def test_agent_status() -> None:
    app, _gw = await _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/agents/test-agent/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == "test-agent"
        assert data["status"] == "idle"


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


async def test_session_preview() -> None:
    app, gw = await _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/sessions/agent:test:main/preview")
        assert resp.status_code == 200
    gw.assert_called_with("sessions.preview", {"keys": ["agent:test:main"]})


async def test_session_reset() -> None:
    app, gw = await _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/sessions/agent:test:main/reset")
        assert resp.status_code == 200
    gw.assert_called_with("sessions.reset", {"key": "agent:test:main"})


async def test_session_delete() -> None:
    app, gw = await _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.delete("/api/sessions/agent:test:main")
        assert resp.status_code == 200
    gw.assert_called_with("sessions.delete", {"key": "agent:test:main"})


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


async def test_config_get() -> None:
    app, gw = await _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["exists"] is True
    gw.assert_called("config.get")


async def test_config_set() -> None:
    app, gw = await _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.put("/api/config", json={"raw": '{"agents": {"new": {}}}'})
        assert resp.status_code == 200
    gw.assert_called_with("config.set", {"raw": '{"agents": {"new": {}}}'})


async def test_config_patch() -> None:
    app, gw = await _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.patch(
            "/api/config",
            json={"raw": '{"agents": {}}', "base_hash": "abc123"},
        )
        assert resp.status_code == 200
    gw.assert_called_with("config.patch", {"raw": '{"agents": {}}', "baseHash": "abc123"})


async def test_config_patch_no_hash() -> None:
    app, gw = await _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.patch("/api/config", json={"raw": '{"x": 1}'})
        assert resp.status_code == 200
    gw.assert_called_with("config.patch", {"raw": '{"x": 1}'})


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


async def test_metrics_costs_not_configured() -> None:
    app, _gw = await _make_app(with_cost_tracker=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/metrics/costs")
        assert resp.status_code == 404


async def test_metrics_costs() -> None:
    app, _gw = await _make_app(with_cost_tracker=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/metrics/costs")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_cost_usd" in data


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------


async def test_webhooks_not_configured() -> None:
    app, _gw = await _make_app(with_webhooks=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/webhooks")
        assert resp.status_code == 404


async def test_webhooks_list_empty() -> None:
    app, _gw = await _make_app(with_webhooks=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/webhooks")
        assert resp.status_code == 200
        assert resp.json() == []


async def test_webhooks_register() -> None:
    app, _gw = await _make_app(with_webhooks=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/webhooks", json={
            "name": "test-hook",
            "url": "https://example.com/hook",
            "events": ["execute"],
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "test-hook"


async def test_webhooks_unregister() -> None:
    app, _gw = await _make_app(with_webhooks=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Register first
        await ac.post("/api/webhooks", json={
            "name": "to-remove",
            "url": "https://example.com/hook",
        })
        # Then unregister
        resp = await ac.delete("/api/webhooks/to-remove")
        assert resp.status_code == 200
        assert resp.json()["removed"] is True


async def test_webhooks_unregister_not_found() -> None:
    app, _gw = await _make_app(with_webhooks=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.delete("/api/webhooks/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------


async def test_workflow_list_presets() -> None:
    app, _gw = await _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/workflows/presets")
        assert resp.status_code == 200
        data = resp.json()
        assert "review" in data
        assert "research" in data
        assert "support" in data


async def test_workflow_run_unknown_preset() -> None:
    app, _gw = await _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/workflows/unknown/run", json={"args": {}})
        assert resp.status_code == 404


async def test_workflow_run_missing_args() -> None:
    app, _gw = await _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/workflows/review/run", json={"args": {}})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


async def test_audit_not_configured() -> None:
    app, _gw = await _make_app(with_audit=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/audit")
        assert resp.status_code == 404


async def test_audit_query() -> None:
    app, _gw = await _make_app(with_audit=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/audit")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert data[0]["event_type"] == "execute"


async def test_audit_query_with_filters() -> None:
    app, _gw = await _make_app(with_audit=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/audit", params={
            "event_type": "execute",
            "agent_id": "test-agent",
            "limit": 10,
        })
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Billing
# ---------------------------------------------------------------------------


async def test_billing_not_configured() -> None:
    app, _gw = await _make_app(with_billing=False)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/billing/usage", params={"tenant_id": "t1"})
        assert resp.status_code == 404


async def test_billing_usage() -> None:
    app, _gw = await _make_app(with_billing=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/billing/usage", params={"tenant_id": "tenant-1"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["tenant_id"] == "tenant-1"
        assert data["total_queries"] == 1


async def test_billing_invoice() -> None:
    app, _gw = await _make_app(with_billing=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/billing/invoice/tenant-1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tenant_id"] == "tenant-1"
        assert "line_items" in data


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


async def test_templates_list() -> None:
    app, _gw = await _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/templates")
        assert resp.status_code == 200
        data = resp.json()
        assert "assistant" in data
        assert "customer-support" in data


async def test_templates_get() -> None:
    app, _gw = await _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/templates/assistant")
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_id"] == "assistant"


async def test_templates_get_not_found() -> None:
    app, _gw = await _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/templates/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Connectors
# ---------------------------------------------------------------------------


async def test_connectors_list() -> None:
    app, _gw = await _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/connectors")
        assert resp.status_code == 200
        data = resp.json()
        assert "GitHubConnector" in data
        assert "SlackConnector" in data


# ---------------------------------------------------------------------------
# Schedules
# ---------------------------------------------------------------------------


async def test_schedules_list() -> None:
    app, gw = await _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/schedules")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "daily-check"


async def test_schedules_delete() -> None:
    app, gw = await _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.delete("/api/schedules/job-1")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True
    gw.assert_called_with("cron.remove", {"id": "job-1"})


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------


async def test_channels_status() -> None:
    app, gw = await _make_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/channels/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "channels" in data
        assert data["channels"]["whatsapp"]["configured"] is True

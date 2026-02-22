"""Dashboard application factory.

Creates a FastAPI app wired to an :class:`OpenClawClient` and optional
managers (audit, billing, webhooks, cost tracker).

Usage::

    from openclaw_sdk.dashboard import create_dashboard_app

    app = create_dashboard_app(client)
    # uvicorn.run(app, host="0.0.0.0", port=8000)

Requires the ``dashboard`` extra::

    pip install openclaw-sdk[dashboard]
"""
from __future__ import annotations

from typing import TYPE_CHECKING

try:
    from fastapi import FastAPI
except ImportError as _err:  # pragma: no cover
    raise ImportError(
        "FastAPI is required for openclaw_sdk.dashboard. "
        "Install it with: pip install openclaw-sdk[dashboard]"
    ) from _err

import structlog

if TYPE_CHECKING:
    from openclaw_sdk.audit.logger import AuditLogger
    from openclaw_sdk.billing.engine import BillingManager
    from openclaw_sdk.core.client import OpenClawClient
    from openclaw_sdk.tracking.cost import CostTracker
    from openclaw_sdk.webhooks.manager import WebhookManager

logger = structlog.get_logger(__name__)


def create_dashboard_app(
    client: OpenClawClient,
    *,
    audit_logger: AuditLogger | None = None,
    billing_manager: BillingManager | None = None,
    webhook_manager: WebhookManager | None = None,
    cost_tracker: CostTracker | None = None,
) -> FastAPI:
    """Create a FastAPI application with REST endpoints for all SDK features.

    Args:
        client: A connected :class:`OpenClawClient` instance.
        audit_logger: Optional :class:`AuditLogger` for audit endpoints.
        billing_manager: Optional :class:`BillingManager` for billing endpoints.
        webhook_manager: Optional :class:`WebhookManager` for webhook endpoints.
        cost_tracker: Optional :class:`CostTracker` for metrics endpoints.

    Returns:
        A configured :class:`FastAPI` application.
    """
    app = FastAPI(title="OpenClaw Dashboard", version="2.0.0")

    # Store references on app.state for router access.
    app.state.client = client
    app.state.audit_logger = audit_logger
    app.state.billing_manager = billing_manager
    app.state.webhook_manager = webhook_manager
    app.state.cost_tracker = cost_tracker

    # Import routers lazily to avoid circular imports.
    from openclaw_sdk.dashboard.routers.agents import router as agents_router
    from openclaw_sdk.dashboard.routers.audit_router import router as audit_router
    from openclaw_sdk.dashboard.routers.billing_router import router as billing_router
    from openclaw_sdk.dashboard.routers.channels_router import router as channels_router
    from openclaw_sdk.dashboard.routers.config import router as config_router
    from openclaw_sdk.dashboard.routers.connectors_router import (
        router as connectors_router,
    )
    from openclaw_sdk.dashboard.routers.health import router as health_router
    from openclaw_sdk.dashboard.routers.metrics import router as metrics_router
    from openclaw_sdk.dashboard.routers.schedules_router import (
        router as schedules_router,
    )
    from openclaw_sdk.dashboard.routers.sessions import router as sessions_router
    from openclaw_sdk.dashboard.routers.templates_router import (
        router as templates_router,
    )
    from openclaw_sdk.dashboard.routers.webhooks_router import (
        router as webhooks_router,
    )
    from openclaw_sdk.dashboard.routers.workflows_router import (
        router as workflows_router,
    )

    app.include_router(health_router)
    app.include_router(agents_router)
    app.include_router(sessions_router)
    app.include_router(config_router)
    app.include_router(metrics_router)
    app.include_router(webhooks_router)
    app.include_router(workflows_router)
    app.include_router(audit_router)
    app.include_router(billing_router)
    app.include_router(templates_router)
    app.include_router(connectors_router)
    app.include_router(schedules_router)
    app.include_router(channels_router)

    logger.info("dashboard_app_created", routers=13)
    return app

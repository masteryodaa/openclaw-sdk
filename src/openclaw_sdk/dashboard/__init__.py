"""Dashboard module — FastAPI application factory for the OpenClaw SDK.

Exposes REST API endpoints for all SDK features including agents, sessions,
config, metrics, webhooks, workflows, audit, billing, templates, connectors,
schedules, and channels.

Requires the ``dashboard`` extra::

    pip install openclaw-sdk[dashboard]
"""
from __future__ import annotations

from openclaw_sdk.dashboard.app import create_dashboard_app

__all__ = ["create_dashboard_app"]

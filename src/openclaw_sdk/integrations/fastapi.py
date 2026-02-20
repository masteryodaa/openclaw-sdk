"""FastAPI integration helpers for the OpenClaw SDK.

Usage::

    from openclaw_sdk.integrations.fastapi import (
        get_openclaw_client,
        create_agent_router,
        create_channel_router,
        create_admin_router,
    )

    app = FastAPI()
    app.include_router(create_agent_router(client, prefix="/agents"))
    app.include_router(create_channel_router(client, prefix="/channels"))
    app.include_router(create_admin_router(client, prefix="/admin"))

Requires the ``fastapi`` extra::

    pip install openclaw-sdk[fastapi]
"""

from __future__ import annotations

import os
from typing import Any

try:
    from fastapi import APIRouter, HTTPException
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel as _FaBaseModel
except ImportError as _err:  # pragma: no cover
    raise ImportError(
        "FastAPI is required for openclaw_sdk.integrations.fastapi. "
        "Install it with: pip install openclaw-sdk[fastapi]"
    ) from _err

from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import ClientConfig, ExecutionOptions
from openclaw_sdk.core.exceptions import ConfigurationError, GatewayError, OpenClawError


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class _ExecuteRequest(_FaBaseModel):
    query: str
    session_name: str = "main"
    timeout_seconds: int = 300
    idempotency_key: str | None = None


class _ExecuteResponse(_FaBaseModel):
    success: bool
    content: str
    latency_ms: int


class _HealthResponse(_FaBaseModel):
    healthy: bool
    latency_ms: float | None = None
    version: str | None = None
    details: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Dependency: shared client
# ---------------------------------------------------------------------------

_CLIENT_SINGLETON: OpenClawClient | None = None


async def get_openclaw_client() -> OpenClawClient:
    """FastAPI dependency that returns a shared :class:`OpenClawClient`.

    Reads ``OPENCLAW_GATEWAY_WS_URL`` and ``OPENCLAW_API_KEY`` from environment
    on first call and caches the connected client for subsequent requests.

    Raises:
        HTTPException 503: If the gateway is unavailable.
    """
    global _CLIENT_SINGLETON
    if _CLIENT_SINGLETON is None:
        try:
            config = ClientConfig(
                gateway_ws_url=os.environ.get("OPENCLAW_GATEWAY_WS_URL"),
                openai_base_url=os.environ.get("OPENCLAW_OPENAI_BASE_URL"),
                api_key=os.environ.get("OPENCLAW_API_KEY"),
            )
            _CLIENT_SINGLETON = await OpenClawClient.connect(
                **{k: v for k, v in config.model_dump().items() if v is not None}
            )
        except (ConfigurationError, GatewayError) as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _CLIENT_SINGLETON


# ---------------------------------------------------------------------------
# Router factories
# ---------------------------------------------------------------------------


def create_agent_router(
    client: OpenClawClient,
    prefix: str = "/agents",
) -> APIRouter:
    """Return an :class:`APIRouter` with agent-related endpoints.

    Endpoints:
        - ``GET  {prefix}/health``       — gateway health check
        - ``POST {prefix}/{agent_id}/execute`` — execute a query against an agent
    """
    router = APIRouter(prefix=prefix, tags=["agents"])

    @router.get("/health", response_model=_HealthResponse)
    async def agent_health() -> _HealthResponse:
        status = await client.health()
        return _HealthResponse(
            healthy=status.healthy,
            latency_ms=status.latency_ms,
            version=status.version,
            details=status.details,
        )

    @router.post("/{agent_id}/execute", response_model=_ExecuteResponse)
    async def execute_agent(
        agent_id: str,
        body: _ExecuteRequest,
    ) -> _ExecuteResponse:
        agent = client.get_agent(agent_id, body.session_name)
        options = ExecutionOptions(timeout_seconds=body.timeout_seconds)
        try:
            result = await agent.execute(
                body.query,
                options=options,
                idempotency_key=body.idempotency_key,
            )
        except OpenClawError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return _ExecuteResponse(
            success=result.success,
            content=result.content,
            latency_ms=result.latency_ms,
        )

    return router


def create_channel_router(
    client: OpenClawClient,
    prefix: str = "/channels",
) -> APIRouter:
    """Return an :class:`APIRouter` with channel management endpoints.

    Endpoints:
        - ``GET  {prefix}/status``        — all channel statuses
        - ``POST {prefix}/{channel}/logout`` — logout a channel
        - ``POST {prefix}/{channel}/login/start`` — start QR login
        - ``POST {prefix}/{channel}/login/wait``  — wait for QR scan
    """
    router = APIRouter(prefix=prefix, tags=["channels"])

    @router.get("/status")
    async def channel_status() -> JSONResponse:
        try:
            result = await client.channels.status()
        except OpenClawError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return JSONResponse(content=result)

    @router.post("/{channel}/logout")
    async def channel_logout(channel: str) -> JSONResponse:
        try:
            result = await client.channels.logout(channel)
        except OpenClawError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return JSONResponse(content=result)

    @router.post("/{channel}/login/start")
    async def channel_login_start(channel: str) -> JSONResponse:
        try:
            result = await client.channels.web_login_start(channel)
        except OpenClawError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return JSONResponse(content=result)

    @router.post("/{channel}/login/wait")
    async def channel_login_wait(channel: str, timeout_ms: int = 60000) -> JSONResponse:
        try:
            result = await client.channels.web_login_wait(channel, timeout_ms)
        except OpenClawError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return JSONResponse(content=result)

    return router


def create_admin_router(
    client: OpenClawClient,
    prefix: str = "/admin",
) -> APIRouter:
    """Return an :class:`APIRouter` with administrative endpoints.

    Endpoints:
        - ``GET  {prefix}/schedules``          — list cron jobs
        - ``POST {prefix}/schedules``          — create a cron job
        - ``DELETE {prefix}/schedules/{job_id}`` — delete a cron job
        - ``GET  {prefix}/skills``             — list installed skills
        - ``POST {prefix}/skills/{name}/install`` — install a skill
    """
    router = APIRouter(prefix=prefix, tags=["admin"])

    @router.get("/schedules")
    async def list_schedules() -> JSONResponse:
        try:
            jobs = await client.scheduling.list_schedules()
        except OpenClawError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return JSONResponse(content=[j.model_dump() for j in jobs])

    @router.delete("/schedules/{job_id}")
    async def delete_schedule(job_id: str) -> JSONResponse:
        try:
            result = await client.scheduling.delete_schedule(job_id)
        except OpenClawError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return JSONResponse(content=result)

    @router.get("/skills")
    async def list_skills() -> JSONResponse:
        try:
            skills = await client.skills.list_skills()
        except OpenClawError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return JSONResponse(content=[s.model_dump() for s in skills])

    @router.post("/skills/{name}/install")
    async def install_skill(name: str) -> JSONResponse:
        try:
            result = await client.skills.install_skill(name)
        except OpenClawError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return JSONResponse(content=result.model_dump())

    return router

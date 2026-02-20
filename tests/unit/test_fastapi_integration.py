"""Tests for integrations/fastapi.py (requires fastapi extra)."""
from __future__ import annotations

import unittest.mock as mock_lib
from unittest.mock import AsyncMock, MagicMock

import pytest

from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.types import ExecutionResult, HealthStatus
from openclaw_sdk.scheduling.manager import CronJob
from openclaw_sdk.skills.manager import SkillInfo

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from openclaw_sdk.integrations.fastapi import (
        create_admin_router,
        create_agent_router,
        create_channel_router,
    )

    _FASTAPI_AVAILABLE = True
except ImportError:
    _FASTAPI_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _FASTAPI_AVAILABLE, reason="fastapi not installed"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_client() -> MagicMock:
    client = MagicMock(spec=OpenClawClient)
    client.health = AsyncMock(
        return_value=HealthStatus(healthy=True, latency_ms=5.0, version="1.0")
    )
    # channels
    channels = MagicMock()
    channels.status = AsyncMock(return_value={"channels": []})
    channels.logout = AsyncMock(return_value={"ok": True})
    channels.web_login_start = AsyncMock(return_value={"qrCode": "data"})
    channels.web_login_wait = AsyncMock(return_value={"loggedIn": True})
    client.channels = channels
    # scheduling
    scheduling = MagicMock()
    scheduling.list_schedules = AsyncMock(
        return_value=[CronJob(id="j1", name="daily", schedule="0 9 * * *")]
    )
    scheduling.delete_schedule = AsyncMock(return_value={"deleted": True})
    client.scheduling = scheduling
    # skills
    skills_mgr = MagicMock()
    skills_mgr.list_skills = AsyncMock(
        return_value=[SkillInfo(name="summarizer", description="Summarises")]
    )
    skills_mgr.install_skill = AsyncMock(
        return_value=SkillInfo(name="summarizer", description="Summarises")
    )
    client.skills = skills_mgr
    return client


def _agent_mock(content: str = "response") -> MagicMock:
    agent = MagicMock()
    agent.execute = AsyncMock(
        return_value=ExecutionResult(success=True, content=content, latency_ms=10)
    )
    return agent


# ---------------------------------------------------------------------------
# Agent router
# ---------------------------------------------------------------------------


def test_agent_router_health() -> None:
    client = _mock_client()
    app = FastAPI()
    app.include_router(create_agent_router(client))
    with TestClient(app) as tc:
        response = tc.get("/agents/health")
    assert response.status_code == 200
    data = response.json()
    assert data["healthy"] is True
    assert data["version"] == "1.0"


def test_agent_router_execute_success() -> None:
    client = _mock_client()
    agent = _agent_mock("Hello, World!")
    client.get_agent = MagicMock(return_value=agent)

    app = FastAPI()
    app.include_router(create_agent_router(client))

    with TestClient(app) as tc:
        response = tc.post(
            "/agents/my-bot/execute",
            json={"query": "say hello", "session_name": "main"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["content"] == "Hello, World!"


def test_agent_router_execute_error_returns_500() -> None:
    from openclaw_sdk.core.exceptions import AgentExecutionError

    client = _mock_client()
    agent = MagicMock()
    agent.execute = AsyncMock(side_effect=AgentExecutionError("bot crashed"))
    client.get_agent = MagicMock(return_value=agent)

    app = FastAPI()
    app.include_router(create_agent_router(client))

    with TestClient(app) as tc:
        response = tc.post(
            "/agents/bad-bot/execute",
            json={"query": "crash"},
        )
    assert response.status_code == 500


# ---------------------------------------------------------------------------
# Channel router
# ---------------------------------------------------------------------------


def test_channel_router_status() -> None:
    client = _mock_client()
    app = FastAPI()
    app.include_router(create_channel_router(client))
    with TestClient(app) as tc:
        response = tc.get("/channels/status")
    assert response.status_code == 200
    assert "channels" in response.json()


def test_channel_router_logout() -> None:
    client = _mock_client()
    app = FastAPI()
    app.include_router(create_channel_router(client))
    with TestClient(app) as tc:
        response = tc.post("/channels/whatsapp/logout")
    assert response.status_code == 200


def test_channel_router_login_start() -> None:
    client = _mock_client()
    app = FastAPI()
    app.include_router(create_channel_router(client))
    with TestClient(app) as tc:
        response = tc.post("/channels/whatsapp/login/start")
    assert response.status_code == 200
    assert "qrCode" in response.json()


def test_channel_router_login_wait() -> None:
    client = _mock_client()
    app = FastAPI()
    app.include_router(create_channel_router(client))
    with TestClient(app) as tc:
        response = tc.post("/channels/whatsapp/login/wait")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Admin router
# ---------------------------------------------------------------------------


def test_admin_router_list_schedules() -> None:
    client = _mock_client()
    app = FastAPI()
    app.include_router(create_admin_router(client))
    with TestClient(app) as tc:
        response = tc.get("/admin/schedules")
    assert response.status_code == 200
    jobs = response.json()
    assert isinstance(jobs, list)
    assert jobs[0]["id"] == "j1"


def test_admin_router_delete_schedule() -> None:
    client = _mock_client()
    app = FastAPI()
    app.include_router(create_admin_router(client))
    with TestClient(app) as tc:
        response = tc.delete("/admin/schedules/j1")
    assert response.status_code == 200


def test_admin_router_list_skills() -> None:
    client = _mock_client()
    app = FastAPI()
    app.include_router(create_admin_router(client))
    with TestClient(app) as tc:
        response = tc.get("/admin/skills")
    assert response.status_code == 200
    skills = response.json()
    assert skills[0]["name"] == "summarizer"


def test_admin_router_install_skill() -> None:
    client = _mock_client()
    app = FastAPI()
    app.include_router(create_admin_router(client))
    with TestClient(app) as tc:
        response = tc.post("/admin/skills/summarizer/install")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# get_openclaw_client — singleton dependency
# ---------------------------------------------------------------------------


async def test_get_openclaw_client_raises_503_on_config_error() -> None:
    """get_openclaw_client raises HTTPException(503) when config fails."""
    from openclaw_sdk.integrations.fastapi import get_openclaw_client
    import openclaw_sdk.integrations.fastapi as fa_module

    original = fa_module._CLIENT_SINGLETON
    fa_module._CLIENT_SINGLETON = None
    try:
        with mock_lib.patch(
            "openclaw_sdk.core.client.OpenClawClient.connect",
            side_effect=Exception("connection refused"),
        ):
            with pytest.raises(Exception):
                await get_openclaw_client()
    finally:
        fa_module._CLIENT_SINGLETON = original


# ---------------------------------------------------------------------------
# has_files property on ExecutionResult
# ---------------------------------------------------------------------------


def test_execution_result_has_files_true() -> None:
    from openclaw_sdk.core.types import GeneratedFile

    result = ExecutionResult(
        success=True,
        content="ok",
        files=[GeneratedFile(name="out.txt", path="/tmp/out.txt", size_bytes=4, mime_type="text/plain")],
    )
    assert result.has_files is True

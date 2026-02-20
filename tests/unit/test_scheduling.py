from __future__ import annotations

from typing import Any

import pytest

from openclaw_sdk.gateway.mock import MockGateway
from openclaw_sdk.scheduling.manager import CronJob, ScheduleConfig, ScheduleManager

# ---------------------------------------------------------------------------
# list_schedules
# ---------------------------------------------------------------------------


async def test_list_schedules_empty(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register("cron.list", {"jobs": []})
    manager = ScheduleManager(connected_mock_gateway)
    result = await manager.list_schedules()
    assert result == []
    connected_mock_gateway.assert_called_with("cron.list", {})


async def test_list_schedules_returns_cron_jobs(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register(
        "cron.list",
        {
            "jobs": [
                {
                    "id": "job_1",
                    "name": "morning",
                    "schedule": "0 9 * * *",
                    "sessionTarget": "agent:main:main",
                    "payload": "good morning",
                    "enabled": True,
                }
            ]
        },
    )
    manager = ScheduleManager(connected_mock_gateway)
    result = await manager.list_schedules()

    assert len(result) == 1
    job = result[0]
    assert isinstance(job, CronJob)
    assert job.name == "morning"
    assert job.schedule == "0 9 * * *"
    assert job.session_target == "agent:main:main"
    assert job.payload == "good morning"


# ---------------------------------------------------------------------------
# create_schedule
# ---------------------------------------------------------------------------


async def test_create_schedule(connected_mock_gateway: MockGateway) -> None:
    job: dict[str, Any] = {
        "id": "job_1",
        "name": "daily",
        "schedule": "0 9 * * *",
        "sessionTarget": "agent:main:main",
        "payload": "run daily report",
        "enabled": True,
    }
    connected_mock_gateway.register("cron.add", job)
    manager = ScheduleManager(connected_mock_gateway)
    config = ScheduleConfig(
        name="daily",
        schedule="0 9 * * *",
        session_target="agent:main:main",
        payload="run daily report",
    )
    result = await manager.create_schedule(config)

    assert isinstance(result, CronJob)
    assert result.name == "daily"
    assert result.id == "job_1"
    # Verify the correct gateway params were used (camelCase on the wire).
    connected_mock_gateway.assert_called_with(
        "cron.add",
        {
            "name": "daily",
            "schedule": "0 9 * * *",
            "sessionTarget": "agent:main:main",
            "payload": "run daily report",
        },
    )


async def test_create_schedule_maps_session_target(connected_mock_gateway: MockGateway) -> None:
    """session_target (Python) must map to sessionTarget (gateway)."""
    connected_mock_gateway.register(
        "cron.add",
        {
            "id": "job_2",
            "name": "weekly",
            "schedule": "0 9 * * 1",
            "sessionTarget": "agent:researcher:main",
            "payload": "weekly digest",
        },
    )
    manager = ScheduleManager(connected_mock_gateway)
    config = ScheduleConfig(
        name="weekly",
        schedule="0 9 * * 1",
        session_target="agent:researcher:main",
        payload="weekly digest",
    )
    await manager.create_schedule(config)
    # Confirm camelCase key was used, not snake_case.
    connected_mock_gateway.assert_called_with(
        "cron.add",
        {
            "name": "weekly",
            "schedule": "0 9 * * 1",
            "sessionTarget": "agent:researcher:main",
            "payload": "weekly digest",
        },
    )


# ---------------------------------------------------------------------------
# cron_status
# ---------------------------------------------------------------------------


async def test_cron_status(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register(
        "cron.status", {"enabled": True, "storePath": "/tmp/cron"}
    )
    manager = ScheduleManager(connected_mock_gateway)
    result = await manager.cron_status()
    assert result["enabled"] is True
    connected_mock_gateway.assert_called_with("cron.status", {})


# ---------------------------------------------------------------------------
# update_schedule
# ---------------------------------------------------------------------------


async def test_update_schedule(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register("cron.update", {"ok": True})
    manager = ScheduleManager(connected_mock_gateway)
    result = await manager.update_schedule("job_1", {"enabled": False})
    assert result["ok"] is True
    connected_mock_gateway.assert_called_with(
        "cron.update", {"id": "job_1", "enabled": False}
    )


# ---------------------------------------------------------------------------
# delete_schedule
# ---------------------------------------------------------------------------


async def test_delete_schedule(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register("cron.remove", {"ok": True})
    manager = ScheduleManager(connected_mock_gateway)
    result = await manager.delete_schedule("job_1")
    assert result is True
    connected_mock_gateway.assert_called_with("cron.remove", {"id": "job_1"})


# ---------------------------------------------------------------------------
# run_now
# ---------------------------------------------------------------------------


async def test_run_now(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register("cron.run", {"runId": "run_abc"})
    manager = ScheduleManager(connected_mock_gateway)
    result = await manager.run_now("job_1")
    assert result["runId"] == "run_abc"
    connected_mock_gateway.assert_called_with("cron.run", {"id": "job_1"})


# ---------------------------------------------------------------------------
# get_runs
# ---------------------------------------------------------------------------


async def test_get_runs(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register(
        "cron.runs",
        {"runs": [{"runId": "run_1", "status": "ok"}, {"runId": "run_2", "status": "error"}]},
    )
    manager = ScheduleManager(connected_mock_gateway)
    result = await manager.get_runs("job_1")
    assert len(result) == 2
    assert result[0]["runId"] == "run_1"
    connected_mock_gateway.assert_called_with("cron.runs", {"id": "job_1"})


async def test_get_runs_empty(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register("cron.runs", {"runs": []})
    manager = ScheduleManager(connected_mock_gateway)
    result = await manager.get_runs("job_99")
    assert result == []


# ---------------------------------------------------------------------------
# wake
# ---------------------------------------------------------------------------


async def test_wake_defaults(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register("wake", {"ok": True})
    manager = ScheduleManager(connected_mock_gateway)
    result = await manager.wake()
    assert result["ok"] is True
    connected_mock_gateway.assert_called_with("wake", {"mode": "now", "text": ""})


async def test_wake_custom_args(connected_mock_gateway: MockGateway) -> None:
    connected_mock_gateway.register("wake", {"ok": True})
    manager = ScheduleManager(connected_mock_gateway)
    await manager.wake(mode="scheduled", text="hello agent")
    connected_mock_gateway.assert_called_with(
        "wake", {"mode": "scheduled", "text": "hello agent"}
    )


# ---------------------------------------------------------------------------
# error propagation
# ---------------------------------------------------------------------------


async def test_raises_when_not_connected(mock_gateway: MockGateway) -> None:
    mock_gateway.register("cron.list", {"jobs": []})
    manager = ScheduleManager(mock_gateway)
    with pytest.raises(RuntimeError, match="not connected"):
        await manager.list_schedules()

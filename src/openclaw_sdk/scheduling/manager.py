from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from openclaw_sdk.gateway.base import GatewayProtocol


class ScheduleConfig(BaseModel):
    """Cron job configuration.

    Field names match the real OpenClaw gateway API (verified against protocol-notes.md):
    - schedule: cron expression  (plan.md originally said "cron_expression" — WRONG)
    - session_target: session key like "agent:main:main"  (plan.md said "agent_id" — WRONG)
    - payload: message string to send  (plan.md said "query" — WRONG)
    """

    name: str
    schedule: str  # cron expression, e.g. "0 9 * * *"
    session_target: str  # e.g. "agent:main:main"  (gateway field: "sessionTarget")
    payload: str  # message to send when job fires
    enabled: bool = True

    model_config = {"populate_by_name": True}


class CronJob(BaseModel):
    """A cron job as returned by the gateway."""

    id: str | None = None
    name: str
    schedule: str | dict[str, Any]  # cron expression or schedule object
    session_target: str = Field(alias="sessionTarget", default="")
    payload: str | dict[str, Any] = ""  # message string or payload object
    enabled: bool = True
    last_run: int | None = Field(default=None, alias="lastRun")
    next_run: int | None = Field(default=None, alias="nextRun")

    model_config = {"populate_by_name": True}


class ScheduleManager:
    """Thin wrapper around the gateway cron.* methods.

    All business logic lives in OpenClaw. This class just translates
    Python method calls into the correct gateway RPC calls.
    """

    def __init__(self, gateway: GatewayProtocol) -> None:
        self._gateway = gateway

    async def list_schedules(self) -> list[CronJob]:
        result = await self._gateway.call("cron.list", {})
        return [CronJob(**item) for item in result.get("jobs", [])]

    async def cron_status(self) -> dict[str, Any]:
        return await self._gateway.call("cron.status", {})

    async def create_schedule(self, config: ScheduleConfig) -> CronJob:
        params: dict[str, Any] = {
            "name": config.name,
            "schedule": config.schedule,
            "sessionTarget": config.session_target,
            "payload": config.payload,
        }
        result = await self._gateway.call("cron.add", params)
        return CronJob(**result)

    async def update_schedule(self, job_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        return await self._gateway.call("cron.update", {"id": job_id, **patch})

    async def delete_schedule(self, job_id: str) -> bool:
        await self._gateway.call("cron.remove", {"id": job_id})
        return True

    async def run_now(self, job_id: str) -> dict[str, Any]:
        return await self._gateway.call("cron.run", {"id": job_id})

    async def get_runs(self, job_id: str) -> list[dict[str, Any]]:
        result = await self._gateway.call("cron.runs", {"id": job_id})
        runs: list[dict[str, Any]] = result.get("runs", [])
        return runs

    async def wake(self, mode: str = "now", text: str = "") -> dict[str, Any]:
        return await self._gateway.call("wake", {"mode": mode, "text": text})

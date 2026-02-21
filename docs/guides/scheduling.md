# Scheduling

The scheduling system lets you run agent tasks on a recurring basis using cron
expressions. Scheduled jobs trigger agent sessions automatically — useful for
periodic reports, monitoring, data syncing, and maintenance routines.

## Schedule Manager

The `ScheduleManager` is available as `client.schedules` and provides full CRUD
operations plus manual triggering.

```python
import asyncio
from openclaw_sdk import OpenClawClient

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        schedules = client.schedules

        # List all schedules
        jobs = await schedules.list_schedules()
        for job in jobs:
            print(f"{job.name} — {job.schedule} — active: {job.active}")

asyncio.run(main())
```

## Creating a Schedule

Use `ScheduleConfig` to define a new scheduled task, then create it with the manager.

```python
import asyncio
from openclaw_sdk import OpenClawClient, ScheduleConfig

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        config = ScheduleConfig(
            name="daily-report",
            schedule="0 9 * * *",          # Every day at 09:00 UTC
            session_target="agent:reporter:daily",
            payload={"prompt": "Generate the daily status report."},
        )

        job = await client.schedules.create_schedule(config)
        print(f"Created schedule: {job.id}")

asyncio.run(main())
```

### ScheduleConfig Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Human-readable name for the schedule |
| `schedule` | `str` | Cron expression (5 or 6 fields) |
| `session_target` | `str` | Session key to trigger (`agent:{id}:{name}`) |
| `payload` | `dict` | Data passed to the agent session on each run |

!!! note
    The `session_target` follows the standard session key format:
    `agent:{agent_id}:{session_name}`. The agent must exist before the
    schedule fires.

## Cron Expression Format

OpenClaw uses standard 5-field cron expressions. An optional 6th field for seconds
is supported.

```
┌───────────── minute (0-59)
│ ┌───────────── hour (0-23)
│ │ ┌───────────── day of month (1-31)
│ │ │ ┌───────────── month (1-12)
│ │ │ │ ┌───────────── day of week (0-7, 0 and 7 = Sunday)
│ │ │ │ │
* * * * *
```

### Common Patterns

| Expression | Description |
|------------|-------------|
| `* * * * *` | Every minute |
| `0 * * * *` | Every hour at :00 |
| `0 9 * * *` | Daily at 09:00 |
| `0 9 * * 1-5` | Weekdays at 09:00 |
| `0 0 1 * *` | First day of every month at midnight |
| `*/15 * * * *` | Every 15 minutes |
| `0 9,17 * * *` | At 09:00 and 17:00 daily |

!!! tip
    All cron times are evaluated in UTC. If your agents operate across time zones,
    convert your desired local time to UTC before setting the schedule.

## Updating a Schedule

Modify an existing schedule by passing its ID and a new config.

```python
from openclaw_sdk import ScheduleConfig

updated_config = ScheduleConfig(
    name="daily-report",
    schedule="0 8 * * 1-5",               # Changed to weekdays at 08:00
    session_target="agent:reporter:daily",
    payload={"prompt": "Generate the weekday status report."},
)

await client.schedules.update_schedule(job_id, updated_config)
```

## Deleting a Schedule

```python
await client.schedules.delete_schedule(job_id)
```

!!! warning
    Deleting a schedule is permanent. Any in-progress run triggered by the schedule
    will complete, but no future runs will fire.

## Manual Triggering

Run a scheduled job immediately, outside its normal cron cadence.

```python
run = await client.schedules.run_now(job_id)
print(f"Manual run started: {run.run_id}")
```

## Viewing Run History

Inspect past executions of a schedule.

```python
runs = await client.schedules.get_runs(job_id)
for run in runs:
    print(f"{run.run_id} — {run.status} — {run.started_at}")
```

## Wake

The `wake()` method nudges the scheduler to re-evaluate all schedules immediately.
This is useful after bulk updates.

```python
await client.schedules.wake()
```

## CronJob Model

Methods that return schedule data use the `CronJob` model.

```python
from openclaw_sdk import CronJob

# CronJob fields:
# job.id          — unique schedule identifier
# job.name        — human-readable name
# job.schedule    — cron expression string
# job.session_target — target session key
# job.payload     — dict passed on each trigger
# job.active      — whether the schedule is enabled
# job.last_run    — datetime of last execution (or None)
# job.next_run    — datetime of next scheduled execution
```

## Full Example

```python
import asyncio
from openclaw_sdk import OpenClawClient, ScheduleConfig

async def main():
    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        schedules = client.schedules

        # Create multiple schedules
        morning_report = await schedules.create_schedule(
            ScheduleConfig(
                name="morning-report",
                schedule="0 9 * * 1-5",
                session_target="agent:reporter:morning",
                payload={"prompt": "Summarize overnight alerts."},
            )
        )

        health_check = await schedules.create_schedule(
            ScheduleConfig(
                name="health-check",
                schedule="*/30 * * * *",
                session_target="agent:monitor:health",
                payload={"prompt": "Run system health checks."},
            )
        )

        # List all to confirm
        jobs = await schedules.list_schedules()
        for job in jobs:
            print(f"{job.name}: next run at {job.next_run}")

        # Trigger the health check manually right now
        run = await schedules.run_now(health_check.id)
        print(f"Health check started: {run.run_id}")

        # View run history
        runs = await schedules.get_runs(health_check.id)
        for r in runs:
            print(f"  {r.run_id} — {r.status}")

asyncio.run(main())
```

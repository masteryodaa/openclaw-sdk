from __future__ import annotations

import json
import subprocess
from typing import Any

from pydantic import BaseModel, Field


class ClawHubSkill(BaseModel):
    name: str
    description: str
    author: str = ""
    version: str = ""
    downloads: int = 0
    rating: float = 0.0
    category: str | None = None
    required_config: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class ClawHub:
    """Browse and discover skills from the ClawHub marketplace via CLI.

    ClawHub is CLI-only — there is no gateway RPC for skill discovery.
    """

    def __init__(self, openclaw_bin: str = "openclaw") -> None:
        self._bin = openclaw_bin

    def _run(self, *args: str) -> Any:
        result = subprocess.run(
            [self._bin, *args, "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"openclaw CLI error: {result.stderr.strip()}")
        return json.loads(result.stdout)

    async def search(self, query: str, limit: int = 20) -> list[ClawHubSkill]:
        data: Any = self._run("skills", "search", query)
        items: list[Any] = data if isinstance(data, list) else data.get("skills", [])
        return [ClawHubSkill(**item) for item in items[:limit]]

    async def browse(
        self, category: str | None = None, limit: int = 20
    ) -> list[ClawHubSkill]:
        args = ["skills", "browse"]
        if category:
            args += ["--category", category]
        data: Any = self._run(*args)
        items: list[Any] = data if isinstance(data, list) else data.get("skills", [])
        return [ClawHubSkill(**item) for item in items[:limit]]

    async def get_details(self, name: str) -> ClawHubSkill:
        data: Any = self._run("skills", "info", name)
        return ClawHubSkill(**data)

    async def get_categories(self) -> list[str]:
        data: Any = self._run("skills", "categories")
        result: list[str] = data if isinstance(data, list) else data.get("categories", [])
        return result

    async def get_trending(self, limit: int = 10) -> list[ClawHubSkill]:
        data: Any = self._run("skills", "trending")
        items: list[Any] = data if isinstance(data, list) else data.get("skills", [])
        return [ClawHubSkill(**item) for item in items[:limit]]

from __future__ import annotations

import json
import subprocess
from typing import Any, Literal

from pydantic import BaseModel


class SkillInfo(BaseModel):
    name: str
    description: str | None = None
    source: Literal["clawhub", "local", "git"] | None = None
    version: str | None = None
    enabled: bool = True


class SkillManager:
    """Manages OpenClaw skills via the CLI (skills are NOT gateway RPC methods).

    Skills are CLI-only: openclaw skills list/info/check.
    This class shells out to the openclaw CLI.
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

    async def list_skills(self) -> list[SkillInfo]:
        data: Any = self._run("skills", "list")
        if isinstance(data, list):
            return [SkillInfo(**item) for item in data]
        return [SkillInfo(**item) for item in data.get("skills", [])]

    async def install_skill(
        self, name: str, source: str = "clawhub", config: dict[str, Any] | None = None
    ) -> SkillInfo:
        args = ["skills", "install", name]
        if source and source != "clawhub":
            args += ["--source", source]
        data: Any = self._run(*args)
        return SkillInfo(**data) if isinstance(data, dict) else SkillInfo(name=name)

    async def uninstall_skill(self, name: str) -> bool:
        self._run("skills", "uninstall", name)
        return True

    async def enable_skill(self, name: str) -> bool:
        self._run("skills", "enable", name)
        return True

    async def disable_skill(self, name: str) -> bool:
        self._run("skills", "disable", name)
        return True

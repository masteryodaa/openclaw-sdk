"""SkillManager — manages OpenClaw skills via CLI and gateway RPC.

Provides two paths for interacting with skills:

**CLI methods** (legacy, subprocess-based):
    - :meth:`list_skills` / :meth:`install_skill` / :meth:`uninstall_skill`
    - :meth:`enable_skill` / :meth:`disable_skill`

**Gateway RPC methods** (preferred when a gateway is available):
    - :meth:`status` — ``skills.status``
    - :meth:`install_via_gateway` — ``skills.install``
    - :meth:`update_skill` — ``skills.update``

The gateway methods require a :class:`GatewayProtocol` instance to be passed
at construction time (or via :attr:`_gateway`).  When accessed through
:attr:`OpenClawClient.skills`, the gateway is injected automatically.
"""

from __future__ import annotations

import json
import subprocess
from typing import Any, Literal

from pydantic import BaseModel

from openclaw_sdk.gateway.base import GatewayProtocol


class SkillInfo(BaseModel):
    name: str
    description: str | None = None
    source: Literal["clawhub", "local", "git"] | None = None
    version: str | None = None
    enabled: bool = True


class SkillManager:
    """Manages OpenClaw skills via CLI fallback and gateway RPC.

    When ``gateway`` is provided, the :meth:`status`, :meth:`install_via_gateway`,
    and :meth:`update_skill` methods delegate to the gateway RPC layer.
    The original CLI methods (:meth:`list_skills`, :meth:`install_skill`, etc.)
    remain available regardless.
    """

    def __init__(
        self,
        openclaw_bin: str = "openclaw",
        gateway: GatewayProtocol | None = None,
    ) -> None:
        self._bin = openclaw_bin
        self._gateway = gateway

    # ------------------------------------------------------------------ #
    # CLI helpers (legacy)
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    # CLI methods (legacy — subprocess-backed)
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    # Gateway RPC methods (preferred when gateway is available)
    # ------------------------------------------------------------------ #

    async def status(self) -> dict[str, Any]:
        """Get full skills status via gateway RPC.

        Gateway method: ``skills.status``

        Returns:
            Dict with ``workspaceDir``, ``managedSkillsDir``, and ``skills``
            array containing skill descriptors.

        Raises:
            RuntimeError: If no gateway is configured.
        """
        if self._gateway is None:
            raise RuntimeError(
                "Gateway required for skills.status -- set gateway on SkillManager"
            )
        return await self._gateway.call("skills.status", {})

    async def install_via_gateway(self, name: str, install_id: str) -> dict[str, Any]:
        """Install a skill via gateway RPC.

        Gateway method: ``skills.install``

        Args:
            name: The skill name to install.
            install_id: Unique installation identifier.

        Raises:
            RuntimeError: If no gateway is configured.
        """
        if self._gateway is None:
            raise RuntimeError("Gateway required for skills.install")
        return await self._gateway.call(
            "skills.install", {"name": name, "installId": install_id}
        )

    async def update_skill(self, skill_key: str) -> dict[str, Any]:
        """Update a skill via gateway RPC.

        Gateway method: ``skills.update``

        Args:
            skill_key: The skill key identifying the skill to update.

        Raises:
            RuntimeError: If no gateway is configured.
        """
        if self._gateway is None:
            raise RuntimeError("Gateway required for skills.update")
        return await self._gateway.call("skills.update", {"skillKey": skill_key})

"""Phase 6E -- Skills via gateway RPC (4 methods).

Tests cover:
- All 4 gateway facade methods (skills_status, skills_bins, skills_install, skills_update)
- All 3 SkillManager gateway RPC methods (status, install_via_gateway, update_skill)
- RuntimeError when gateway is None
- Existing CLI methods still accessible (no regression)
- Client integration (skills property passes gateway)
"""

from __future__ import annotations

import json
import subprocess
import unittest.mock as mock_lib
from typing import Any

import pytest

from openclaw_sdk.core.client import OpenClawClient
from openclaw_sdk.core.config import ClientConfig
from openclaw_sdk.gateway.mock import MockGateway
from openclaw_sdk.skills.manager import SkillInfo, SkillManager


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


def _make_manager() -> tuple[MockGateway, SkillManager]:
    mock = MockGateway()
    mock._connected = True
    return mock, SkillManager(gateway=mock)


def _make_client() -> tuple[MockGateway, OpenClawClient]:
    mock = MockGateway()
    mock._connected = True
    return mock, OpenClawClient(config=ClientConfig(), gateway=mock)


_SKILLS_STATUS_RESPONSE: dict[str, Any] = {
    "workspaceDir": "/home/user/.openclaw/skills",
    "managedSkillsDir": "/home/user/.openclaw/managed-skills",
    "skills": [
        {
            "name": "web-search",
            "description": "Search the web for information",
            "source": "clawhub",
            "bundled": False,
            "filePath": "/home/user/.openclaw/skills/web-search/skill.json",
            "baseDir": "/home/user/.openclaw/skills/web-search",
            "skillKey": "web-search@1.0.0",
            "emoji": "🔍",
            "always": False,
            "disabled": False,
            "eligible": True,
            "requirements": [],
            "missing": [],
            "configChecks": [],
            "install": {"name": "web-search", "installId": "ws-001"},
        },
        {
            "name": "code-review",
            "description": "Review code for issues",
            "source": "local",
            "bundled": True,
            "filePath": "/home/user/.openclaw/skills/code-review/skill.json",
            "baseDir": "/home/user/.openclaw/skills/code-review",
            "skillKey": "code-review@2.1.0",
            "always": True,
            "disabled": False,
            "eligible": True,
            "requirements": ["git"],
            "missing": [],
            "configChecks": [],
            "install": {"name": "code-review", "installId": "cr-001"},
        },
    ],
}

_SKILLS_BINS_RESPONSE: dict[str, Any] = {
    "bins": [
        {"name": "skill-runner", "path": "/usr/local/bin/skill-runner", "version": "1.2.0"},
    ],
}

_SKILLS_INSTALL_RESPONSE: dict[str, Any] = {
    "ok": True,
    "name": "web-search",
    "installId": "ws-001",
}

_SKILLS_UPDATE_RESPONSE: dict[str, Any] = {
    "ok": True,
    "skillKey": "web-search@1.1.0",
}


# ================================================================== #
# Gateway facade tests
# ================================================================== #


class TestGatewaySkillsStatus:
    async def test_calls_correct_method(self) -> None:
        mock = MockGateway()
        mock._connected = True
        mock.register("skills.status", _SKILLS_STATUS_RESPONSE)

        result = await mock.skills_status()

        mock.assert_called("skills.status")
        assert "skills" in result
        assert "workspaceDir" in result

    async def test_passes_empty_params(self) -> None:
        mock = MockGateway()
        mock._connected = True
        mock.register("skills.status", _SKILLS_STATUS_RESPONSE)

        await mock.skills_status()

        _, params = mock.calls[-1]
        assert params == {}

    async def test_response_structure(self) -> None:
        mock = MockGateway()
        mock._connected = True
        mock.register("skills.status", _SKILLS_STATUS_RESPONSE)

        result = await mock.skills_status()

        assert isinstance(result["skills"], list)
        assert len(result["skills"]) == 2
        skill = result["skills"][0]
        assert skill["name"] == "web-search"
        assert skill["skillKey"] == "web-search@1.0.0"
        assert skill["eligible"] is True


class TestGatewaySkillsBins:
    async def test_calls_correct_method(self) -> None:
        mock = MockGateway()
        mock._connected = True
        mock.register("skills.bins", _SKILLS_BINS_RESPONSE)

        result = await mock.skills_bins()

        mock.assert_called("skills.bins")
        assert "bins" in result

    async def test_passes_empty_params(self) -> None:
        mock = MockGateway()
        mock._connected = True
        mock.register("skills.bins", _SKILLS_BINS_RESPONSE)

        await mock.skills_bins()

        _, params = mock.calls[-1]
        assert params == {}


class TestGatewaySkillsInstall:
    async def test_calls_correct_method(self) -> None:
        mock = MockGateway()
        mock._connected = True
        mock.register("skills.install", _SKILLS_INSTALL_RESPONSE)

        result = await mock.skills_install("web-search", "ws-001")

        mock.assert_called("skills.install")
        assert result["ok"] is True

    async def test_passes_correct_params(self) -> None:
        mock = MockGateway()
        mock._connected = True
        mock.register("skills.install", _SKILLS_INSTALL_RESPONSE)

        await mock.skills_install("web-search", "ws-001")

        _, params = mock.calls[-1]
        assert params == {"name": "web-search", "installId": "ws-001"}


class TestGatewaySkillsUpdate:
    async def test_calls_correct_method(self) -> None:
        mock = MockGateway()
        mock._connected = True
        mock.register("skills.update", _SKILLS_UPDATE_RESPONSE)

        result = await mock.skills_update("web-search@1.0.0")

        mock.assert_called("skills.update")
        assert result["ok"] is True

    async def test_passes_correct_params(self) -> None:
        mock = MockGateway()
        mock._connected = True
        mock.register("skills.update", _SKILLS_UPDATE_RESPONSE)

        await mock.skills_update("web-search@1.0.0")

        _, params = mock.calls[-1]
        assert params == {"skillKey": "web-search@1.0.0"}


# ================================================================== #
# SkillManager gateway RPC method tests
# ================================================================== #


class TestSkillManagerStatus:
    async def test_calls_gateway(self) -> None:
        mock, mgr = _make_manager()
        mock.register("skills.status", _SKILLS_STATUS_RESPONSE)

        result = await mgr.status()

        mock.assert_called("skills.status")
        assert "skills" in result
        assert len(result["skills"]) == 2

    async def test_passes_empty_params(self) -> None:
        mock, mgr = _make_manager()
        mock.register("skills.status", _SKILLS_STATUS_RESPONSE)

        await mgr.status()

        _, params = mock.calls[-1]
        assert params == {}

    async def test_raises_without_gateway(self) -> None:
        mgr = SkillManager()

        with pytest.raises(RuntimeError, match="Gateway required for skills.status"):
            await mgr.status()


class TestSkillManagerInstallViaGateway:
    async def test_calls_gateway(self) -> None:
        mock, mgr = _make_manager()
        mock.register("skills.install", _SKILLS_INSTALL_RESPONSE)

        result = await mgr.install_via_gateway("web-search", "ws-001")

        mock.assert_called("skills.install")
        assert result["ok"] is True

    async def test_passes_correct_params(self) -> None:
        mock, mgr = _make_manager()
        mock.register("skills.install", _SKILLS_INSTALL_RESPONSE)

        await mgr.install_via_gateway("web-search", "ws-001")

        _, params = mock.calls[-1]
        assert params == {"name": "web-search", "installId": "ws-001"}

    async def test_raises_without_gateway(self) -> None:
        mgr = SkillManager()

        with pytest.raises(RuntimeError, match="Gateway required for skills.install"):
            await mgr.install_via_gateway("web-search", "ws-001")


class TestSkillManagerUpdateSkill:
    async def test_calls_gateway(self) -> None:
        mock, mgr = _make_manager()
        mock.register("skills.update", _SKILLS_UPDATE_RESPONSE)

        result = await mgr.update_skill("web-search@1.0.0")

        mock.assert_called("skills.update")
        assert result["ok"] is True

    async def test_passes_correct_params(self) -> None:
        mock, mgr = _make_manager()
        mock.register("skills.update", _SKILLS_UPDATE_RESPONSE)

        await mgr.update_skill("web-search@1.0.0")

        _, params = mock.calls[-1]
        assert params == {"skillKey": "web-search@1.0.0"}

    async def test_raises_without_gateway(self) -> None:
        mgr = SkillManager()

        with pytest.raises(RuntimeError, match="Gateway required for skills.update"):
            await mgr.update_skill("web-search@1.0.0")


# ================================================================== #
# Backward compatibility -- existing CLI methods still work
# ================================================================== #


def _completed(stdout: object, returncode: int = 0) -> mock_lib.MagicMock:
    return mock_lib.MagicMock(
        return_value=subprocess.CompletedProcess(
            args=[],
            returncode=returncode,
            stdout=json.dumps(stdout),
            stderr="",
        )
    )


class TestCLIMethodsStillWork:
    """Existing CLI methods remain functional even with gateway set."""

    async def test_list_skills_still_works(self) -> None:
        data = [{"name": "summarizer", "description": "Summarises text"}]
        mock, mgr = _make_manager()
        with mock_lib.patch("subprocess.run", _completed(data)):
            skills = await mgr.list_skills()
        assert len(skills) == 1
        assert skills[0].name == "summarizer"
        assert isinstance(skills[0], SkillInfo)

    async def test_install_skill_still_works(self) -> None:
        data = {"name": "summarizer", "description": "desc", "enabled": True}
        mock, mgr = _make_manager()
        with mock_lib.patch("subprocess.run", _completed(data)):
            info = await mgr.install_skill("summarizer")
        assert isinstance(info, SkillInfo)
        assert info.name == "summarizer"

    async def test_uninstall_skill_still_works(self) -> None:
        mock, mgr = _make_manager()
        with mock_lib.patch("subprocess.run", _completed({})):
            result = await mgr.uninstall_skill("summarizer")
        assert result is True

    async def test_enable_skill_still_works(self) -> None:
        mock, mgr = _make_manager()
        with mock_lib.patch("subprocess.run", _completed({})):
            result = await mgr.enable_skill("summarizer")
        assert result is True

    async def test_disable_skill_still_works(self) -> None:
        mock, mgr = _make_manager()
        with mock_lib.patch("subprocess.run", _completed({})):
            result = await mgr.disable_skill("summarizer")
        assert result is True

    async def test_cli_methods_work_without_gateway(self) -> None:
        """CLI methods should work even when no gateway is set."""
        data = [{"name": "test-skill", "description": "test"}]
        mgr = SkillManager()  # no gateway
        with mock_lib.patch("subprocess.run", _completed(data)):
            skills = await mgr.list_skills()
        assert len(skills) == 1
        assert skills[0].name == "test-skill"


# ================================================================== #
# Client integration -- skills property routes to SkillManager w/ gateway
# ================================================================== #


class TestClientSkillsIntegration:
    async def test_skills_status_via_client(self) -> None:
        mock, client = _make_client()
        mock.register("skills.status", _SKILLS_STATUS_RESPONSE)

        result = await client.skills.status()

        mock.assert_called("skills.status")
        assert "skills" in result

    async def test_skills_install_via_client(self) -> None:
        mock, client = _make_client()
        mock.register("skills.install", _SKILLS_INSTALL_RESPONSE)

        result = await client.skills.install_via_gateway("web-search", "ws-001")

        mock.assert_called("skills.install")
        assert result["ok"] is True

    async def test_skills_update_via_client(self) -> None:
        mock, client = _make_client()
        mock.register("skills.update", _SKILLS_UPDATE_RESPONSE)

        result = await client.skills.update_skill("web-search@1.0.0")

        mock.assert_called("skills.update")
        assert result["ok"] is True

    async def test_client_skills_has_gateway(self) -> None:
        mock, client = _make_client()

        mgr = client.skills

        assert mgr._gateway is not None
        assert mgr._gateway is mock

    async def test_client_skills_cli_methods_still_accessible(self) -> None:
        """CLI methods are still accessible through client.skills."""
        mock, client = _make_client()
        data = [{"name": "test", "description": "test skill"}]
        with mock_lib.patch("subprocess.run", _completed(data)):
            skills = await client.skills.list_skills()
        assert len(skills) == 1

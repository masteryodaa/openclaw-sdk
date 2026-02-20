"""Tests for skills/manager.py (SkillManager) and skills/clawhub.py (ClawHub)."""
from __future__ import annotations

import json
import subprocess
import unittest.mock as mock_lib

import pytest

from openclaw_sdk.skills.clawhub import ClawHub, ClawHubSkill
from openclaw_sdk.skills.manager import SkillInfo, SkillManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _completed(stdout: object, returncode: int = 0) -> mock_lib.MagicMock:
    return mock_lib.MagicMock(
        return_value=subprocess.CompletedProcess(
            args=[],
            returncode=returncode,
            stdout=json.dumps(stdout),
            stderr="",
        )
    )


def _failed(stderr: str = "CLI error") -> mock_lib.MagicMock:
    return mock_lib.MagicMock(
        return_value=subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr=stderr,
        )
    )


# ---------------------------------------------------------------------------
# SkillManager — list_skills
# ---------------------------------------------------------------------------


async def test_skill_manager_list_skills_returns_list() -> None:
    data = [{"name": "summarizer", "description": "Summarises text"}]
    with mock_lib.patch("subprocess.run", _completed(data)):
        mgr = SkillManager()
        skills = await mgr.list_skills()
    assert len(skills) == 1
    assert skills[0].name == "summarizer"


async def test_skill_manager_list_skills_dict_response() -> None:
    data = {"skills": [{"name": "translator", "description": "Translates text"}]}
    with mock_lib.patch("subprocess.run", _completed(data)):
        mgr = SkillManager()
        skills = await mgr.list_skills()
    assert skills[0].name == "translator"


async def test_skill_manager_list_skills_cli_error_raises() -> None:
    with mock_lib.patch("subprocess.run", _failed("no such command")):
        mgr = SkillManager()
        with pytest.raises(RuntimeError, match="openclaw CLI error"):
            await mgr.list_skills()


# ---------------------------------------------------------------------------
# SkillManager — install_skill
# ---------------------------------------------------------------------------


async def test_skill_manager_install_skill_returns_skill_info() -> None:
    data = {"name": "summarizer", "description": "desc", "enabled": True}
    with mock_lib.patch("subprocess.run", _completed(data)):
        mgr = SkillManager()
        info = await mgr.install_skill("summarizer")
    assert isinstance(info, SkillInfo)
    assert info.name == "summarizer"


async def test_skill_manager_install_skill_non_dict_response() -> None:
    # If the CLI returns a list/unexpected type, fall back to SkillInfo(name=name)
    with mock_lib.patch("subprocess.run", _completed([])):
        mgr = SkillManager()
        info = await mgr.install_skill("my-skill")
    assert info.name == "my-skill"


async def test_skill_manager_install_skill_non_clawhub_source() -> None:
    data = {"name": "custom", "description": "local skill", "source": "local"}
    with mock_lib.patch("subprocess.run", _completed(data)) as mock_run:
        mgr = SkillManager()
        await mgr.install_skill("custom", source="local")
    call_args = mock_run.call_args[0][0]
    assert "--source" in call_args
    assert "local" in call_args


# ---------------------------------------------------------------------------
# SkillManager — uninstall / enable / disable
# ---------------------------------------------------------------------------


async def test_skill_manager_uninstall_returns_true() -> None:
    with mock_lib.patch("subprocess.run", _completed({})):
        mgr = SkillManager()
        result = await mgr.uninstall_skill("summarizer")
    assert result is True


async def test_skill_manager_enable_returns_true() -> None:
    with mock_lib.patch("subprocess.run", _completed({})):
        mgr = SkillManager()
        result = await mgr.enable_skill("summarizer")
    assert result is True


async def test_skill_manager_disable_returns_true() -> None:
    with mock_lib.patch("subprocess.run", _completed({})):
        mgr = SkillManager()
        result = await mgr.disable_skill("summarizer")
    assert result is True


# ---------------------------------------------------------------------------
# ClawHub — search
# ---------------------------------------------------------------------------


async def test_clawhub_search_returns_skills() -> None:
    data = [{"name": "ai-writer", "description": "Writes content", "author": "alice"}]
    with mock_lib.patch("subprocess.run", _completed(data)):
        hub = ClawHub()
        skills = await hub.search("writing")
    assert len(skills) == 1
    assert skills[0].name == "ai-writer"


async def test_clawhub_search_dict_response() -> None:
    data = {"skills": [{"name": "translator", "description": "Translates"}]}
    with mock_lib.patch("subprocess.run", _completed(data)):
        hub = ClawHub()
        skills = await hub.search("translate")
    assert skills[0].name == "translator"


async def test_clawhub_search_respects_limit() -> None:
    data = [{"name": f"skill{i}", "description": "d"} for i in range(10)]
    with mock_lib.patch("subprocess.run", _completed(data)):
        hub = ClawHub()
        skills = await hub.search("skill", limit=3)
    assert len(skills) == 3


# ---------------------------------------------------------------------------
# ClawHub — browse
# ---------------------------------------------------------------------------


async def test_clawhub_browse_returns_skills() -> None:
    data = [{"name": "analyzer", "description": "Analyzes text"}]
    with mock_lib.patch("subprocess.run", _completed(data)):
        hub = ClawHub()
        skills = await hub.browse()
    assert isinstance(skills[0], ClawHubSkill)


async def test_clawhub_browse_with_category_passes_flag() -> None:
    data: list[object] = []
    with mock_lib.patch("subprocess.run", _completed(data)) as mock_run:
        hub = ClawHub()
        await hub.browse(category="nlp")
    call_args = mock_run.call_args[0][0]
    assert "--category" in call_args
    assert "nlp" in call_args


# ---------------------------------------------------------------------------
# ClawHub — get_details
# ---------------------------------------------------------------------------


async def test_clawhub_get_details_returns_skill() -> None:
    data = {"name": "summarizer", "description": "Summarises", "author": "bob"}
    with mock_lib.patch("subprocess.run", _completed(data)):
        hub = ClawHub()
        skill = await hub.get_details("summarizer")
    assert isinstance(skill, ClawHubSkill)
    assert skill.name == "summarizer"
    assert skill.author == "bob"


# ---------------------------------------------------------------------------
# ClawHub — get_categories
# ---------------------------------------------------------------------------


async def test_clawhub_get_categories_list_response() -> None:
    data = ["nlp", "vision", "audio"]
    with mock_lib.patch("subprocess.run", _completed(data)):
        hub = ClawHub()
        cats = await hub.get_categories()
    assert cats == ["nlp", "vision", "audio"]


async def test_clawhub_get_categories_dict_response() -> None:
    data = {"categories": ["nlp", "vision"]}
    with mock_lib.patch("subprocess.run", _completed(data)):
        hub = ClawHub()
        cats = await hub.get_categories()
    assert "nlp" in cats


# ---------------------------------------------------------------------------
# ClawHub — get_trending
# ---------------------------------------------------------------------------


async def test_clawhub_get_trending_returns_skills() -> None:
    data = [{"name": "hot-skill", "description": "Trending"} for _ in range(5)]
    with mock_lib.patch("subprocess.run", _completed(data)):
        hub = ClawHub()
        skills = await hub.get_trending(limit=3)
    assert len(skills) == 3


async def test_clawhub_cli_error_raises() -> None:
    with mock_lib.patch("subprocess.run", _failed("command not found")):
        hub = ClawHub()
        with pytest.raises(RuntimeError, match="openclaw CLI error"):
            await hub.search("anything")

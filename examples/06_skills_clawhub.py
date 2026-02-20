# RUN: python examples/06_skills_clawhub.py
"""Skills and ClawHub — demonstrate SkillManager and ClawHub with mocked subprocess."""

import asyncio
import json
from unittest.mock import MagicMock, patch

from openclaw_sdk.skills.manager import SkillManager
from openclaw_sdk.skills.clawhub import ClawHub


# ---------------------------------------------------------------------------
# Mock subprocess data
# ---------------------------------------------------------------------------

_MOCK_SKILLS_LIST = json.dumps([
    {"name": "email-sender", "description": "Send emails via SMTP", "source": "clawhub",
     "version": "1.2.0", "enabled": True},
    {"name": "slack-notifier", "description": "Post messages to Slack", "source": "clawhub",
     "version": "0.9.1", "enabled": False},
])

_MOCK_SEARCH_RESULTS = json.dumps([
    {"name": "email-sender", "description": "Send emails via SMTP", "author": "openclaw-team",
     "version": "1.2.0", "downloads": 15420, "rating": 4.8, "category": "communication",
     "tags": ["email", "smtp", "notifications"]},
    {"name": "gmail-reader", "description": "Read and search Gmail inbox", "author": "contrib",
     "version": "0.5.0", "downloads": 3210, "rating": 4.2, "category": "communication",
     "tags": ["email", "gmail", "google"]},
])

_MOCK_TRENDING = json.dumps([
    {"name": "web-scraper", "description": "Scrape web pages", "author": "openclaw-team",
     "version": "2.0.0", "downloads": 50000, "rating": 4.9, "category": "data",
     "tags": ["web", "scraping", "html"]},
])

_MOCK_CATEGORIES = json.dumps(["communication", "data", "finance", "devops", "productivity"])


def _make_mock_run(return_value: str):
    """Return a mock for subprocess.run that yields the given JSON string."""
    result = MagicMock()
    result.returncode = 0
    result.stdout = return_value
    result.stderr = ""
    return result


async def main() -> None:
    skill_manager = SkillManager()
    clawhub = ClawHub()

    # ---- SkillManager.list_skills ----------------------------------------
    with patch("subprocess.run", return_value=_make_mock_run(_MOCK_SKILLS_LIST)):
        skills = await skill_manager.list_skills()
    print("Installed skills:")
    for skill in skills:
        status = "enabled" if skill.enabled else "disabled"
        print(f"  {skill.name} v{skill.version}  [{status}]  — {skill.description}")

    # ---- SkillManager.install_skill --------------------------------------
    install_response = json.dumps(
        {"name": "email-sender", "version": "1.2.0", "source": "clawhub", "enabled": True}
    )
    with patch("subprocess.run", return_value=_make_mock_run(install_response)):
        installed = await skill_manager.install_skill("email-sender")
    print(f"\nInstalled: {installed.name} v{installed.version}")

    # ---- ClawHub.search --------------------------------------------------
    with patch("subprocess.run", return_value=_make_mock_run(_MOCK_SEARCH_RESULTS)):
        results = await clawhub.search("email")
    print("\nClawHub search results for 'email':")
    for skill in results:
        print(f"  {skill.name} — {skill.description}  "
              f"(downloads={skill.downloads}, rating={skill.rating})")

    # ---- ClawHub.get_trending --------------------------------------------
    with patch("subprocess.run", return_value=_make_mock_run(_MOCK_TRENDING)):
        trending = await clawhub.get_trending(limit=5)
    print("\nTrending skills:")
    for skill in trending:
        print(f"  {skill.name} — {skill.description}  (downloads={skill.downloads})")

    # ---- ClawHub.get_categories ------------------------------------------
    with patch("subprocess.run", return_value=_make_mock_run(_MOCK_CATEGORIES)):
        categories = await clawhub.get_categories()
    print(f"\nAvailable categories: {categories}")


if __name__ == "__main__":
    asyncio.run(main())

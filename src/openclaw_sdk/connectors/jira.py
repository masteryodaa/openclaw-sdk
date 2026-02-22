"""Jira connector — issues, search, and project management."""

from __future__ import annotations

import base64
from typing import Any

import structlog

from openclaw_sdk.connectors.base import Connector, ConnectorAction, ConnectorConfig

logger = structlog.get_logger(__name__)


class JiraConnector(Connector):
    """Connector for the Jira Cloud REST API v3.

    ``base_url`` must be set to your Atlassian instance
    (e.g. ``"https://yourorg.atlassian.net"``).  Authentication uses
    Basic auth with your email as username and an API token as password
    (``api_key`` = email, ``api_secret`` = API token).

    Usage::

        config = ConnectorConfig(
            api_key="you@company.com",
            api_secret="ATATT3...",
            base_url="https://yourorg.atlassian.net",
        )
        async with JiraConnector(config) as jira:
            issues = await jira.search_issues("project = DEV")
    """

    DEFAULT_BASE_URL = ""  # must be configured per instance

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            **self._config.extra_headers,
        }
        if self._config.api_key and self._config.api_secret:
            creds = f"{self._config.api_key}:{self._config.api_secret}"
            b64 = base64.b64encode(creds.encode()).decode("ascii")
            headers["Authorization"] = f"Basic {b64}"
        return headers

    def list_actions(self) -> list[ConnectorAction]:
        return [
            ConnectorAction(
                name="search_issues",
                description="Search issues using JQL",
                required_params=["jql"],
                optional_params=["max_results"],
            ),
            ConnectorAction(
                name="get_issue",
                description="Get a single issue by key",
                required_params=["issue_key"],
            ),
            ConnectorAction(
                name="create_issue",
                description="Create a new issue",
                required_params=["project_key", "summary", "issue_type"],
                optional_params=["description"],
            ),
            ConnectorAction(
                name="update_issue",
                description="Update an existing issue",
                required_params=["issue_key", "fields"],
            ),
        ]

    async def search_issues(
        self, jql: str, max_results: int = 50
    ) -> dict[str, Any]:
        """Search for issues using JQL.

        Args:
            jql: Jira Query Language expression.
            max_results: Maximum number of results to return.

        Returns:
            Search results with ``issues`` array.
        """
        client = self._ensure_connected()
        resp = await client.get(
            "/rest/api/3/search",
            params={"jql": jql, "maxResults": max_results},
        )
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def get_issue(self, issue_key: str) -> dict[str, Any]:
        """Get a single issue by its key (e.g. ``"DEV-123"``).

        Args:
            issue_key: The Jira issue key.

        Returns:
            Full issue object with fields and metadata.
        """
        client = self._ensure_connected()
        resp = await client.get(f"/rest/api/3/issue/{issue_key}")
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def create_issue(
        self,
        project_key: str,
        summary: str,
        issue_type: str = "Task",
        description: str = "",
    ) -> dict[str, Any]:
        """Create a new Jira issue.

        Args:
            project_key: Project key (e.g. ``"DEV"``).
            summary: Issue summary / title.
            issue_type: Issue type name (e.g. ``"Task"``, ``"Bug"``, ``"Story"``).
            description: Issue description (plain text).

        Returns:
            Created issue object with ``key`` and ``id``.
        """
        client = self._ensure_connected()
        payload: dict[str, Any] = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "issuetype": {"name": issue_type},
            }
        }
        if description:
            payload["fields"]["description"] = {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            }
        resp = await client.post("/rest/api/3/issue", json=payload)
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def update_issue(
        self, issue_key: str, fields: dict[str, Any]
    ) -> None:
        """Update an existing Jira issue.

        Args:
            issue_key: The Jira issue key (e.g. ``"DEV-123"``).
            fields: Dictionary of fields to update.
        """
        client = self._ensure_connected()
        resp = await client.put(
            f"/rest/api/3/issue/{issue_key}",
            json={"fields": fields},
        )
        resp.raise_for_status()

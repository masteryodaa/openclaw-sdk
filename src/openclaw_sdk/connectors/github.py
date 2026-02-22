"""GitHub connector — repositories, issues, and pull requests."""

from __future__ import annotations

from typing import Any

import structlog

from openclaw_sdk.connectors.base import Connector, ConnectorAction, ConnectorConfig

logger = structlog.get_logger(__name__)


class GitHubConnector(Connector):
    """Connector for the GitHub REST API v3.

    Supports listing repositories, fetching repo details, and managing issues.

    Usage::

        config = ConnectorConfig(api_key="ghp_xxx")
        async with GitHubConnector(config) as gh:
            repos = await gh.list_repos(org="myorg")
            issue = await gh.create_issue("owner", "repo", "Bug title")
    """

    DEFAULT_BASE_URL = "https://api.github.com"

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/vnd.github.v3+json",
            **self._config.extra_headers,
        }
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        return headers

    def list_actions(self) -> list[ConnectorAction]:
        return [
            ConnectorAction(
                name="list_repos",
                description="List repositories for the authenticated user or an org",
                optional_params=["org", "per_page"],
            ),
            ConnectorAction(
                name="get_repo",
                description="Get a single repository",
                required_params=["owner", "repo"],
            ),
            ConnectorAction(
                name="create_issue",
                description="Create a new issue",
                required_params=["owner", "repo", "title"],
                optional_params=["body", "labels"],
            ),
            ConnectorAction(
                name="list_issues",
                description="List issues for a repository",
                required_params=["owner", "repo"],
                optional_params=["state", "per_page"],
            ),
            ConnectorAction(
                name="get_issue",
                description="Get a single issue",
                required_params=["owner", "repo", "number"],
            ),
        ]

    async def list_repos(
        self, org: str | None = None, per_page: int = 30
    ) -> list[dict[str, Any]]:
        """List repositories for the authenticated user or an organisation.

        Args:
            org: If provided, list repos for this organisation.
            per_page: Number of results per page (max 100).

        Returns:
            List of repository objects.
        """
        client = self._ensure_connected()
        url = f"/orgs/{org}/repos" if org else "/user/repos"
        resp = await client.get(url, params={"per_page": per_page})
        resp.raise_for_status()
        result: list[dict[str, Any]] = resp.json()
        return result

    async def get_repo(self, owner: str, repo: str) -> dict[str, Any]:
        """Get details of a single repository.

        Args:
            owner: Repository owner (user or org).
            repo: Repository name.

        Returns:
            Repository object.
        """
        client = self._ensure_connected()
        resp = await client.get(f"/repos/{owner}/{repo}")
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str = "",
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new issue on a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            title: Issue title.
            body: Issue body (Markdown).
            labels: Optional list of label names.

        Returns:
            Created issue object.
        """
        client = self._ensure_connected()
        payload: dict[str, Any] = {"title": title, "body": body}
        if labels:
            payload["labels"] = labels
        resp = await client.post(f"/repos/{owner}/{repo}/issues", json=payload)
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def list_issues(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        per_page: int = 30,
    ) -> list[dict[str, Any]]:
        """List issues for a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            state: Issue state filter (``"open"``, ``"closed"``, ``"all"``).
            per_page: Number of results per page.

        Returns:
            List of issue objects.
        """
        client = self._ensure_connected()
        resp = await client.get(
            f"/repos/{owner}/{repo}/issues",
            params={"state": state, "per_page": per_page},
        )
        resp.raise_for_status()
        result: list[dict[str, Any]] = resp.json()
        return result

    async def get_issue(
        self, owner: str, repo: str, number: int
    ) -> dict[str, Any]:
        """Get a single issue by number.

        Args:
            owner: Repository owner.
            repo: Repository name.
            number: Issue number.

        Returns:
            Issue object.
        """
        client = self._ensure_connected()
        resp = await client.get(f"/repos/{owner}/{repo}/issues/{number}")
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

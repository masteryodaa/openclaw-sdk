"""Tests for connectors/ — SaaS connector base + all 10 connectors."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from openclaw_sdk.connectors.base import Connector, ConnectorAction, ConnectorConfig
from openclaw_sdk.connectors.github import GitHubConnector
from openclaw_sdk.connectors.gmail import GmailConnector
from openclaw_sdk.connectors.google_sheets import GoogleSheetsConnector
from openclaw_sdk.connectors.hubspot import HubSpotConnector
from openclaw_sdk.connectors.jira import JiraConnector
from openclaw_sdk.connectors.notion import NotionConnector
from openclaw_sdk.connectors.salesforce import SalesforceConnector
from openclaw_sdk.connectors.slack_connector import SlackConnector
from openclaw_sdk.connectors.stripe_connector import StripeConnector
from openclaw_sdk.connectors.zendesk import ZendeskConnector


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_transport(
    response_data: Any, status: int = 200
) -> httpx.MockTransport:
    """Create a mock transport that returns *response_data* as JSON."""

    async def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=response_data)

    return httpx.MockTransport(_handler)


def _mock_transport_no_body(status: int = 204) -> httpx.MockTransport:
    """Create a mock transport that returns an empty body (e.g. 204)."""

    async def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=b"")

    return httpx.MockTransport(_handler)


def _mock_transport_form(
    response_data: Any, status: int = 200
) -> httpx.MockTransport:
    """Mock transport that also records the request for assertions."""

    async def _handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=response_data)

    return httpx.MockTransport(_handler)


def _attach_mock_client(
    connector: Connector,
    data: Any,
    status: int = 200,
    base_url: str = "https://example.com",
) -> None:
    """Attach a mock httpx client to a connector."""
    connector._client = httpx.AsyncClient(
        base_url=base_url,
        transport=_mock_transport(data, status),
    )


def _attach_mock_client_no_body(
    connector: Connector,
    status: int = 204,
    base_url: str = "https://example.com",
) -> None:
    """Attach a mock httpx client that returns an empty body."""
    connector._client = httpx.AsyncClient(
        base_url=base_url,
        transport=_mock_transport_no_body(status),
    )


# ---------------------------------------------------------------------------
# ConnectorConfig — defaults and validation
# ---------------------------------------------------------------------------


class TestConnectorConfig:
    def test_defaults(self) -> None:
        cfg = ConnectorConfig()
        assert cfg.api_key is None
        assert cfg.api_secret is None
        assert cfg.base_url is None
        assert cfg.timeout == 30.0
        assert cfg.extra_headers == {}

    def test_custom_values(self) -> None:
        cfg = ConnectorConfig(
            api_key="key",
            api_secret="secret",
            base_url="https://api.example.com",
            timeout=60.0,
            extra_headers={"X-Custom": "value"},
        )
        assert cfg.api_key == "key"
        assert cfg.api_secret == "secret"
        assert cfg.base_url == "https://api.example.com"
        assert cfg.timeout == 60.0
        assert cfg.extra_headers == {"X-Custom": "value"}


# ---------------------------------------------------------------------------
# ConnectorAction
# ---------------------------------------------------------------------------


class TestConnectorAction:
    def test_minimal(self) -> None:
        action = ConnectorAction(name="test")
        assert action.name == "test"
        assert action.description == ""
        assert action.required_params == []
        assert action.optional_params == []

    def test_full(self) -> None:
        action = ConnectorAction(
            name="create_item",
            description="Create an item",
            required_params=["title"],
            optional_params=["body"],
        )
        assert action.required_params == ["title"]
        assert action.optional_params == ["body"]


# ---------------------------------------------------------------------------
# Base Connector — context manager and not-connected guard
# ---------------------------------------------------------------------------


class TestBaseConnector:
    async def test_context_manager(self) -> None:
        config = ConnectorConfig(api_key="tok")
        async with GitHubConnector(config) as gh:
            assert gh._client is not None
        assert gh._client is None

    async def test_connect_and_close(self) -> None:
        config = ConnectorConfig(api_key="tok")
        conn = GitHubConnector(config)
        assert conn._client is None
        await conn.connect()
        assert conn._client is not None
        await conn.close()
        assert conn._client is None

    async def test_double_close_safe(self) -> None:
        config = ConnectorConfig(api_key="tok")
        conn = GitHubConnector(config)
        await conn.connect()
        await conn.close()
        await conn.close()  # should not raise

    def test_config_property(self) -> None:
        config = ConnectorConfig(api_key="tok")
        conn = GitHubConnector(config)
        assert conn.config is config


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------


class TestGitHubConnector:
    def test_not_connected(self) -> None:
        conn = GitHubConnector(ConnectorConfig(api_key="tok"))
        with pytest.raises(RuntimeError, match="not connected"):
            conn._ensure_connected()

    def test_actions(self) -> None:
        conn = GitHubConnector(ConnectorConfig(api_key="tok"))
        actions = conn.list_actions()
        names = [a.name for a in actions]
        assert "list_repos" in names
        assert "get_repo" in names
        assert "create_issue" in names
        assert "list_issues" in names
        assert "get_issue" in names

    def test_headers_with_key(self) -> None:
        conn = GitHubConnector(ConnectorConfig(api_key="ghp_xxx"))
        headers = conn._build_headers()
        assert headers["Authorization"] == "Bearer ghp_xxx"
        assert headers["Accept"] == "application/vnd.github.v3+json"

    def test_headers_without_key(self) -> None:
        conn = GitHubConnector(ConnectorConfig())
        headers = conn._build_headers()
        assert "Authorization" not in headers

    async def test_list_repos(self) -> None:
        conn = GitHubConnector(ConnectorConfig(api_key="tok"))
        _attach_mock_client(
            conn,
            [{"full_name": "user/repo1"}],
            base_url="https://api.github.com",
        )
        repos = await conn.list_repos()
        assert len(repos) == 1
        assert repos[0]["full_name"] == "user/repo1"
        await conn.close()

    async def test_list_repos_org(self) -> None:
        conn = GitHubConnector(ConnectorConfig(api_key="tok"))
        _attach_mock_client(
            conn,
            [{"full_name": "myorg/repo1"}],
            base_url="https://api.github.com",
        )
        repos = await conn.list_repos(org="myorg")
        assert repos[0]["full_name"] == "myorg/repo1"
        await conn.close()

    async def test_get_repo(self) -> None:
        conn = GitHubConnector(ConnectorConfig(api_key="tok"))
        _attach_mock_client(
            conn,
            {"full_name": "owner/repo", "id": 42},
            base_url="https://api.github.com",
        )
        repo = await conn.get_repo("owner", "repo")
        assert repo["id"] == 42
        await conn.close()

    async def test_create_issue(self) -> None:
        conn = GitHubConnector(ConnectorConfig(api_key="tok"))
        _attach_mock_client(
            conn,
            {"number": 1, "title": "Bug"},
            status=201,
            base_url="https://api.github.com",
        )
        issue = await conn.create_issue("owner", "repo", "Bug")
        assert issue["number"] == 1
        await conn.close()

    async def test_list_issues(self) -> None:
        conn = GitHubConnector(ConnectorConfig(api_key="tok"))
        _attach_mock_client(
            conn,
            [{"number": 1}, {"number": 2}],
            base_url="https://api.github.com",
        )
        issues = await conn.list_issues("owner", "repo")
        assert len(issues) == 2
        await conn.close()

    async def test_get_issue(self) -> None:
        conn = GitHubConnector(ConnectorConfig(api_key="tok"))
        _attach_mock_client(
            conn,
            {"number": 42, "title": "Found it"},
            base_url="https://api.github.com",
        )
        issue = await conn.get_issue("owner", "repo", 42)
        assert issue["number"] == 42
        await conn.close()


# ---------------------------------------------------------------------------
# Slack
# ---------------------------------------------------------------------------


class TestSlackConnector:
    def test_not_connected(self) -> None:
        conn = SlackConnector(ConnectorConfig(api_key="xoxb-xxx"))
        with pytest.raises(RuntimeError, match="not connected"):
            conn._ensure_connected()

    def test_actions(self) -> None:
        conn = SlackConnector(ConnectorConfig(api_key="xoxb-xxx"))
        actions = conn.list_actions()
        names = [a.name for a in actions]
        assert "send_message" in names
        assert "list_channels" in names
        assert "post_file" in names
        assert "list_users" in names

    def test_headers(self) -> None:
        conn = SlackConnector(ConnectorConfig(api_key="xoxb-xxx"))
        headers = conn._build_headers()
        assert headers["Authorization"] == "Bearer xoxb-xxx"

    async def test_send_message(self) -> None:
        conn = SlackConnector(ConnectorConfig(api_key="xoxb-xxx"))
        _attach_mock_client(
            conn,
            {"ok": True, "ts": "1234.5678"},
            base_url="https://slack.com/api",
        )
        result = await conn.send_message("#general", "Hello!")
        assert result["ok"] is True
        await conn.close()

    async def test_list_channels(self) -> None:
        conn = SlackConnector(ConnectorConfig(api_key="xoxb-xxx"))
        _attach_mock_client(
            conn,
            {"ok": True, "channels": [{"name": "general"}]},
            base_url="https://slack.com/api",
        )
        result = await conn.list_channels()
        assert len(result["channels"]) == 1
        await conn.close()

    async def test_list_users(self) -> None:
        conn = SlackConnector(ConnectorConfig(api_key="xoxb-xxx"))
        _attach_mock_client(
            conn,
            {"ok": True, "members": [{"name": "alice"}]},
            base_url="https://slack.com/api",
        )
        result = await conn.list_users()
        assert result["members"][0]["name"] == "alice"
        await conn.close()


# ---------------------------------------------------------------------------
# Google Sheets
# ---------------------------------------------------------------------------


class TestGoogleSheetsConnector:
    def test_not_connected(self) -> None:
        conn = GoogleSheetsConnector(ConnectorConfig(api_key="ya29"))
        with pytest.raises(RuntimeError, match="not connected"):
            conn._ensure_connected()

    def test_actions(self) -> None:
        conn = GoogleSheetsConnector(ConnectorConfig(api_key="ya29"))
        actions = conn.list_actions()
        names = [a.name for a in actions]
        assert "get_values" in names
        assert "update_values" in names
        assert "list_sheets" in names

    async def test_get_values(self) -> None:
        conn = GoogleSheetsConnector(ConnectorConfig(api_key="ya29"))
        _attach_mock_client(
            conn,
            {"values": [["A1", "B1"], ["A2", "B2"]]},
            base_url="https://sheets.googleapis.com/v4",
        )
        result = await conn.get_values("sheet_id", "Sheet1!A1:B2")
        assert len(result["values"]) == 2
        await conn.close()

    async def test_update_values(self) -> None:
        conn = GoogleSheetsConnector(ConnectorConfig(api_key="ya29"))
        _attach_mock_client(
            conn,
            {"updatedCells": 4},
            base_url="https://sheets.googleapis.com/v4",
        )
        result = await conn.update_values(
            "sheet_id", "Sheet1!A1:B2", [["X", "Y"], ["Z", "W"]]
        )
        assert result["updatedCells"] == 4
        await conn.close()

    async def test_list_sheets(self) -> None:
        conn = GoogleSheetsConnector(ConnectorConfig(api_key="ya29"))
        _attach_mock_client(
            conn,
            {"sheets": [{"properties": {"title": "Sheet1"}}]},
            base_url="https://sheets.googleapis.com/v4",
        )
        result = await conn.list_sheets("sheet_id")
        assert result["sheets"][0]["properties"]["title"] == "Sheet1"
        await conn.close()


# ---------------------------------------------------------------------------
# Gmail
# ---------------------------------------------------------------------------


class TestGmailConnector:
    def test_not_connected(self) -> None:
        conn = GmailConnector(ConnectorConfig(api_key="ya29"))
        with pytest.raises(RuntimeError, match="not connected"):
            conn._ensure_connected()

    def test_actions(self) -> None:
        conn = GmailConnector(ConnectorConfig(api_key="ya29"))
        actions = conn.list_actions()
        names = [a.name for a in actions]
        assert "send_email" in names
        assert "list_messages" in names
        assert "get_message" in names

    def test_encode_message(self) -> None:
        raw = GmailConnector._encode_message("a@b.com", "Hi", "Body")
        assert isinstance(raw, str)
        assert len(raw) > 0

    async def test_send_email(self) -> None:
        conn = GmailConnector(ConnectorConfig(api_key="ya29"))
        _attach_mock_client(
            conn,
            {"id": "msg123", "threadId": "thread456"},
            base_url="https://gmail.googleapis.com/gmail/v1",
        )
        result = await conn.send_email("user@example.com", "Hi", "Body")
        assert result["id"] == "msg123"
        await conn.close()

    async def test_list_messages(self) -> None:
        conn = GmailConnector(ConnectorConfig(api_key="ya29"))
        _attach_mock_client(
            conn,
            {"messages": [{"id": "m1"}, {"id": "m2"}]},
            base_url="https://gmail.googleapis.com/gmail/v1",
        )
        result = await conn.list_messages(query="from:test@test.com")
        assert len(result["messages"]) == 2
        await conn.close()

    async def test_get_message(self) -> None:
        conn = GmailConnector(ConnectorConfig(api_key="ya29"))
        _attach_mock_client(
            conn,
            {"id": "m1", "snippet": "Hello"},
            base_url="https://gmail.googleapis.com/gmail/v1",
        )
        result = await conn.get_message("m1")
        assert result["snippet"] == "Hello"
        await conn.close()


# ---------------------------------------------------------------------------
# Notion
# ---------------------------------------------------------------------------


class TestNotionConnector:
    def test_not_connected(self) -> None:
        conn = NotionConnector(ConnectorConfig(api_key="ntn_xxx"))
        with pytest.raises(RuntimeError, match="not connected"):
            conn._ensure_connected()

    def test_actions(self) -> None:
        conn = NotionConnector(ConnectorConfig(api_key="ntn_xxx"))
        actions = conn.list_actions()
        names = [a.name for a in actions]
        assert "search" in names
        assert "get_page" in names
        assert "create_page" in names
        assert "get_database" in names

    def test_headers_include_notion_version(self) -> None:
        conn = NotionConnector(ConnectorConfig(api_key="ntn_xxx"))
        headers = conn._build_headers()
        assert headers["Notion-Version"] == "2022-06-28"
        assert headers["Authorization"] == "Bearer ntn_xxx"

    async def test_search(self) -> None:
        conn = NotionConnector(ConnectorConfig(api_key="ntn_xxx"))
        _attach_mock_client(
            conn,
            {"results": [{"id": "page1"}]},
            base_url="https://api.notion.com/v1",
        )
        result = await conn.search("My Page")
        assert len(result["results"]) == 1
        await conn.close()

    async def test_get_page(self) -> None:
        conn = NotionConnector(ConnectorConfig(api_key="ntn_xxx"))
        _attach_mock_client(
            conn,
            {"id": "page1", "object": "page"},
            base_url="https://api.notion.com/v1",
        )
        result = await conn.get_page("page1")
        assert result["object"] == "page"
        await conn.close()

    async def test_create_page(self) -> None:
        conn = NotionConnector(ConnectorConfig(api_key="ntn_xxx"))
        _attach_mock_client(
            conn,
            {"id": "new-page", "object": "page"},
            base_url="https://api.notion.com/v1",
        )
        result = await conn.create_page("parent1", {"title": [{}]})
        assert result["id"] == "new-page"
        await conn.close()

    async def test_create_page_in_database(self) -> None:
        conn = NotionConnector(ConnectorConfig(api_key="ntn_xxx"))
        _attach_mock_client(
            conn,
            {"id": "new-page-db", "object": "page"},
            base_url="https://api.notion.com/v1",
        )
        result = await conn.create_page(
            "db-id", {"Name": {"title": [{}]}}, is_database=True
        )
        assert result["id"] == "new-page-db"
        await conn.close()

    async def test_get_database(self) -> None:
        conn = NotionConnector(ConnectorConfig(api_key="ntn_xxx"))
        _attach_mock_client(
            conn,
            {"id": "db1", "object": "database"},
            base_url="https://api.notion.com/v1",
        )
        result = await conn.get_database("db1")
        assert result["object"] == "database"
        await conn.close()


# ---------------------------------------------------------------------------
# Jira
# ---------------------------------------------------------------------------


class TestJiraConnector:
    def test_not_connected(self) -> None:
        conn = JiraConnector(
            ConnectorConfig(
                api_key="user@co.com",
                api_secret="token",
                base_url="https://test.atlassian.net",
            )
        )
        with pytest.raises(RuntimeError, match="not connected"):
            conn._ensure_connected()

    def test_actions(self) -> None:
        conn = JiraConnector(
            ConnectorConfig(base_url="https://test.atlassian.net")
        )
        actions = conn.list_actions()
        names = [a.name for a in actions]
        assert "search_issues" in names
        assert "get_issue" in names
        assert "create_issue" in names
        assert "update_issue" in names

    def test_headers_basic_auth(self) -> None:
        conn = JiraConnector(
            ConnectorConfig(
                api_key="user@co.com",
                api_secret="token123",
                base_url="https://test.atlassian.net",
            )
        )
        headers = conn._build_headers()
        assert headers["Authorization"].startswith("Basic ")

    async def test_search_issues(self) -> None:
        conn = JiraConnector(
            ConnectorConfig(
                api_key="user@co.com",
                api_secret="tok",
                base_url="https://test.atlassian.net",
            )
        )
        _attach_mock_client(
            conn,
            {"issues": [{"key": "DEV-1"}], "total": 1},
            base_url="https://test.atlassian.net",
        )
        result = await conn.search_issues("project = DEV")
        assert result["total"] == 1
        await conn.close()

    async def test_get_issue(self) -> None:
        conn = JiraConnector(
            ConnectorConfig(
                api_key="user@co.com",
                api_secret="tok",
                base_url="https://test.atlassian.net",
            )
        )
        _attach_mock_client(
            conn,
            {"key": "DEV-42", "fields": {"summary": "Test"}},
            base_url="https://test.atlassian.net",
        )
        result = await conn.get_issue("DEV-42")
        assert result["key"] == "DEV-42"
        await conn.close()

    async def test_create_issue(self) -> None:
        conn = JiraConnector(
            ConnectorConfig(
                api_key="user@co.com",
                api_secret="tok",
                base_url="https://test.atlassian.net",
            )
        )
        _attach_mock_client(
            conn,
            {"key": "DEV-100", "id": "10100"},
            status=201,
            base_url="https://test.atlassian.net",
        )
        result = await conn.create_issue("DEV", "New task", "Task", "Details")
        assert result["key"] == "DEV-100"
        await conn.close()

    async def test_update_issue(self) -> None:
        conn = JiraConnector(
            ConnectorConfig(
                api_key="user@co.com",
                api_secret="tok",
                base_url="https://test.atlassian.net",
            )
        )
        _attach_mock_client_no_body(
            conn, status=204, base_url="https://test.atlassian.net"
        )
        # update_issue returns None (204 No Content)
        await conn.update_issue("DEV-42", {"summary": "Updated"})
        await conn.close()


# ---------------------------------------------------------------------------
# Stripe
# ---------------------------------------------------------------------------


class TestStripeConnector:
    def test_not_connected(self) -> None:
        conn = StripeConnector(ConnectorConfig(api_key="sk_test_xxx"))
        with pytest.raises(RuntimeError, match="not connected"):
            conn._ensure_connected()

    def test_actions(self) -> None:
        conn = StripeConnector(ConnectorConfig(api_key="sk_test_xxx"))
        actions = conn.list_actions()
        names = [a.name for a in actions]
        assert "list_customers" in names
        assert "create_customer" in names
        assert "list_charges" in names
        assert "get_charge" in names

    async def test_list_customers(self) -> None:
        conn = StripeConnector(ConnectorConfig(api_key="sk_test_xxx"))
        _attach_mock_client(
            conn,
            {"data": [{"id": "cus_1"}], "has_more": False},
            base_url="https://api.stripe.com/v1",
        )
        result = await conn.list_customers(limit=5)
        assert result["data"][0]["id"] == "cus_1"
        await conn.close()

    async def test_create_customer(self) -> None:
        conn = StripeConnector(ConnectorConfig(api_key="sk_test_xxx"))
        _attach_mock_client(
            conn,
            {"id": "cus_new", "email": "test@test.com"},
            base_url="https://api.stripe.com/v1",
        )
        result = await conn.create_customer(email="test@test.com", name="Test")
        assert result["id"] == "cus_new"
        await conn.close()

    async def test_get_charge(self) -> None:
        conn = StripeConnector(ConnectorConfig(api_key="sk_test_xxx"))
        _attach_mock_client(
            conn,
            {"id": "ch_1", "amount": 2000},
            base_url="https://api.stripe.com/v1",
        )
        result = await conn.get_charge("ch_1")
        assert result["amount"] == 2000
        await conn.close()

    async def test_connect_creates_client(self) -> None:
        conn = StripeConnector(ConnectorConfig(api_key="sk_test_xxx"))
        await conn.connect()
        assert conn._client is not None
        await conn.close()


# ---------------------------------------------------------------------------
# HubSpot
# ---------------------------------------------------------------------------


class TestHubSpotConnector:
    def test_not_connected(self) -> None:
        conn = HubSpotConnector(ConnectorConfig(api_key="pat-xxx"))
        with pytest.raises(RuntimeError, match="not connected"):
            conn._ensure_connected()

    def test_actions(self) -> None:
        conn = HubSpotConnector(ConnectorConfig(api_key="pat-xxx"))
        actions = conn.list_actions()
        names = [a.name for a in actions]
        assert "list_contacts" in names
        assert "create_contact" in names
        assert "list_deals" in names
        assert "get_deal" in names

    def test_headers(self) -> None:
        conn = HubSpotConnector(ConnectorConfig(api_key="pat-xxx"))
        headers = conn._build_headers()
        assert headers["Authorization"] == "Bearer pat-xxx"

    async def test_list_contacts(self) -> None:
        conn = HubSpotConnector(ConnectorConfig(api_key="pat-xxx"))
        _attach_mock_client(
            conn,
            {"results": [{"id": "1", "properties": {"email": "a@b.com"}}]},
            base_url="https://api.hubapi.com",
        )
        result = await conn.list_contacts(limit=5)
        assert len(result["results"]) == 1
        await conn.close()

    async def test_create_contact(self) -> None:
        conn = HubSpotConnector(ConnectorConfig(api_key="pat-xxx"))
        _attach_mock_client(
            conn,
            {"id": "101", "properties": {"email": "new@co.com"}},
            base_url="https://api.hubapi.com",
        )
        result = await conn.create_contact(
            "new@co.com", properties={"firstname": "New"}
        )
        assert result["id"] == "101"
        await conn.close()

    async def test_get_deal(self) -> None:
        conn = HubSpotConnector(ConnectorConfig(api_key="pat-xxx"))
        _attach_mock_client(
            conn,
            {"id": "deal1", "properties": {"dealname": "Big Deal"}},
            base_url="https://api.hubapi.com",
        )
        result = await conn.get_deal("deal1")
        assert result["properties"]["dealname"] == "Big Deal"
        await conn.close()

    async def test_list_deals(self) -> None:
        conn = HubSpotConnector(ConnectorConfig(api_key="pat-xxx"))
        _attach_mock_client(
            conn,
            {"results": [{"id": "d1"}, {"id": "d2"}]},
            base_url="https://api.hubapi.com",
        )
        result = await conn.list_deals(limit=10)
        assert len(result["results"]) == 2
        await conn.close()


# ---------------------------------------------------------------------------
# Salesforce
# ---------------------------------------------------------------------------


class TestSalesforceConnector:
    def test_not_connected(self) -> None:
        conn = SalesforceConnector(
            ConnectorConfig(
                api_key="00D...",
                base_url="https://test.my.salesforce.com",
            )
        )
        with pytest.raises(RuntimeError, match="not connected"):
            conn._ensure_connected()

    def test_actions(self) -> None:
        conn = SalesforceConnector(
            ConnectorConfig(base_url="https://test.my.salesforce.com")
        )
        actions = conn.list_actions()
        names = [a.name for a in actions]
        assert "query" in names
        assert "get_record" in names
        assert "create_record" in names
        assert "update_record" in names

    def test_headers(self) -> None:
        conn = SalesforceConnector(
            ConnectorConfig(
                api_key="token123",
                base_url="https://test.my.salesforce.com",
            )
        )
        headers = conn._build_headers()
        assert headers["Authorization"] == "Bearer token123"

    async def test_query(self) -> None:
        conn = SalesforceConnector(
            ConnectorConfig(
                api_key="tok",
                base_url="https://test.my.salesforce.com",
            )
        )
        _attach_mock_client(
            conn,
            {"totalSize": 2, "records": [{"Id": "001"}, {"Id": "002"}]},
            base_url="https://test.my.salesforce.com",
        )
        result = await conn.query("SELECT Id FROM Account LIMIT 2")
        assert result["totalSize"] == 2
        await conn.close()

    async def test_get_record(self) -> None:
        conn = SalesforceConnector(
            ConnectorConfig(
                api_key="tok",
                base_url="https://test.my.salesforce.com",
            )
        )
        _attach_mock_client(
            conn,
            {"Id": "001", "Name": "Acme"},
            base_url="https://test.my.salesforce.com",
        )
        result = await conn.get_record("Account", "001")
        assert result["Name"] == "Acme"
        await conn.close()

    async def test_create_record(self) -> None:
        conn = SalesforceConnector(
            ConnectorConfig(
                api_key="tok",
                base_url="https://test.my.salesforce.com",
            )
        )
        _attach_mock_client(
            conn,
            {"id": "001new", "success": True},
            status=201,
            base_url="https://test.my.salesforce.com",
        )
        result = await conn.create_record("Account", {"Name": "NewCo"})
        assert result["success"] is True
        await conn.close()

    async def test_update_record(self) -> None:
        conn = SalesforceConnector(
            ConnectorConfig(
                api_key="tok",
                base_url="https://test.my.salesforce.com",
            )
        )
        _attach_mock_client_no_body(
            conn, status=204, base_url="https://test.my.salesforce.com"
        )
        # update_record returns None (204 No Content)
        await conn.update_record("Account", "001", {"Name": "Updated"})
        await conn.close()


# ---------------------------------------------------------------------------
# Zendesk
# ---------------------------------------------------------------------------


class TestZendeskConnector:
    def test_not_connected(self) -> None:
        conn = ZendeskConnector(
            ConnectorConfig(
                api_key="agent@co.com",
                api_secret="zd_token",
                base_url="https://test.zendesk.com/api/v2",
            )
        )
        with pytest.raises(RuntimeError, match="not connected"):
            conn._ensure_connected()

    def test_actions(self) -> None:
        conn = ZendeskConnector(
            ConnectorConfig(base_url="https://test.zendesk.com/api/v2")
        )
        actions = conn.list_actions()
        names = [a.name for a in actions]
        assert "list_tickets" in names
        assert "get_ticket" in names
        assert "create_ticket" in names
        assert "update_ticket" in names

    def test_headers_basic_auth(self) -> None:
        conn = ZendeskConnector(
            ConnectorConfig(
                api_key="agent@co.com",
                api_secret="zd_token",
                base_url="https://test.zendesk.com/api/v2",
            )
        )
        headers = conn._build_headers()
        assert headers["Authorization"].startswith("Basic ")

    async def test_list_tickets(self) -> None:
        conn = ZendeskConnector(
            ConnectorConfig(
                api_key="agent@co.com",
                api_secret="zd_token",
                base_url="https://test.zendesk.com/api/v2",
            )
        )
        _attach_mock_client(
            conn,
            {"tickets": [{"id": 1, "subject": "Help!"}]},
            base_url="https://test.zendesk.com/api/v2",
        )
        result = await conn.list_tickets(status="open")
        assert len(result["tickets"]) == 1
        await conn.close()

    async def test_get_ticket(self) -> None:
        conn = ZendeskConnector(
            ConnectorConfig(
                api_key="agent@co.com",
                api_secret="zd_token",
                base_url="https://test.zendesk.com/api/v2",
            )
        )
        _attach_mock_client(
            conn,
            {"ticket": {"id": 42, "subject": "Found it"}},
            base_url="https://test.zendesk.com/api/v2",
        )
        result = await conn.get_ticket(42)
        assert result["ticket"]["id"] == 42
        await conn.close()

    async def test_create_ticket(self) -> None:
        conn = ZendeskConnector(
            ConnectorConfig(
                api_key="agent@co.com",
                api_secret="zd_token",
                base_url="https://test.zendesk.com/api/v2",
            )
        )
        _attach_mock_client(
            conn,
            {"ticket": {"id": 100, "subject": "New ticket"}},
            status=201,
            base_url="https://test.zendesk.com/api/v2",
        )
        result = await conn.create_ticket("New ticket", "Please help")
        assert result["ticket"]["id"] == 100
        await conn.close()

    async def test_update_ticket(self) -> None:
        conn = ZendeskConnector(
            ConnectorConfig(
                api_key="agent@co.com",
                api_secret="zd_token",
                base_url="https://test.zendesk.com/api/v2",
            )
        )
        _attach_mock_client(
            conn,
            {"ticket": {"id": 42, "status": "solved"}},
            base_url="https://test.zendesk.com/api/v2",
        )
        result = await conn.update_ticket(42, {"status": "solved"})
        assert result["ticket"]["status"] == "solved"
        await conn.close()


# ---------------------------------------------------------------------------
# Cross-cutting: all connectors importable from __init__
# ---------------------------------------------------------------------------


class TestImports:
    def test_all_exports(self) -> None:
        """Verify the __init__.py exports all expected names."""
        import openclaw_sdk.connectors as mod

        assert hasattr(mod, "Connector")
        assert hasattr(mod, "ConnectorConfig")
        assert hasattr(mod, "ConnectorAction")
        assert hasattr(mod, "GitHubConnector")
        assert hasattr(mod, "SlackConnector")
        assert hasattr(mod, "GoogleSheetsConnector")
        assert hasattr(mod, "GmailConnector")
        assert hasattr(mod, "NotionConnector")
        assert hasattr(mod, "JiraConnector")
        assert hasattr(mod, "StripeConnector")
        assert hasattr(mod, "HubSpotConnector")
        assert hasattr(mod, "SalesforceConnector")
        assert hasattr(mod, "ZendeskConnector")

    def test_all_list_complete(self) -> None:
        """Ensure __all__ contains all 13 expected names."""
        from openclaw_sdk.connectors import __all__

        assert len(__all__) == 13

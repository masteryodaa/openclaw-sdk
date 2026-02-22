# SaaS Connectors

The OpenClaw SDK ships with pre-built connectors for 10 popular SaaS APIs.
Every connector uses `httpx` for real HTTP API calls, supports the async
context manager protocol, and exposes a consistent `Connector` interface
so you can swap services without rewriting your application logic.

## Quick Start

```python
import asyncio
from openclaw_sdk.connectors import GitHubConnector, ConnectorConfig

async def main():
    config = ConnectorConfig(api_key="ghp_your_token_here")

    async with GitHubConnector(config) as gh:
        repos = await gh.list_repos(per_page=5)
        for repo in repos:
            print(f"{repo['full_name']} - {repo['stargazers_count']} stars")

        issue = await gh.create_issue(
            owner="myorg",
            repo="myproject",
            title="Bug: login page crashes",
            body="Steps to reproduce...",
            labels=["bug"],
        )
        print(f"Created issue #{issue['number']}")

asyncio.run(main())
```

## Connector ABC

All connectors extend the `Connector` abstract base class. This guarantees
a consistent lifecycle and interface across all 10 services.

### Lifecycle

| Method      | Description                                         |
|-------------|-----------------------------------------------------|
| `connect()` | Open the underlying `httpx.AsyncClient`             |
| `close()`   | Close the underlying `httpx.AsyncClient`            |

Every connector supports `async with`, which calls `connect()` on entry and
`close()` on exit:

```python
async with SlackConnector(config) as slack:
    await slack.send_message("#general", "Hello!")
    # client is automatically closed when the block exits
```

### Discovering Actions

Every connector exposes a `list_actions()` method that returns a list of
`ConnectorAction` objects describing what the connector can do:

```python
async with GitHubConnector(config) as gh:
    for action in gh.list_actions():
        print(f"{action.name}: {action.description}")
        print(f"  Required: {action.required_params}")
        print(f"  Optional: {action.optional_params}")
```

## ConnectorConfig

All connectors are configured with a single `ConnectorConfig` Pydantic model.

| Parameter       | Type              | Default | Description                                   |
|-----------------|-------------------|---------|-----------------------------------------------|
| `api_key`       | `str | None`      | `None`  | Primary API key or OAuth access token         |
| `api_secret`    | `str | None`      | `None`  | Secondary secret (e.g. API token for Basic auth) |
| `base_url`      | `str | None`      | `None`  | Override the default API base URL             |
| `timeout`       | `float`           | `30.0`  | HTTP request timeout in seconds               |
| `extra_headers` | `dict[str, str]`  | `{}`    | Additional headers merged into every request  |

!!! tip "Base URL overrides"
    Most connectors have a sensible `DEFAULT_BASE_URL` built in. Use
    `base_url` only when pointing at a self-hosted instance, a proxy,
    or a staging environment.

## ConnectorAction

Describes a single action a connector can perform.

| Field             | Type         | Description                              |
|-------------------|--------------|------------------------------------------|
| `name`            | `str`        | Machine-readable action name             |
| `description`     | `str`        | Human-readable description               |
| `required_params` | `list[str]`  | Parameter names that must be provided    |
| `optional_params` | `list[str]`  | Parameter names that may be omitted      |

## Available Connectors

### GitHub

Connector for the GitHub REST API v3. Manage repositories, issues, and pull requests.

**Auth:** Personal access token or GitHub App token as `api_key`.

| Action         | Description                          | Required Params        | Optional Params   |
|----------------|--------------------------------------|------------------------|-------------------|
| `list_repos`   | List repos for the user or an org    | --                     | `org`, `per_page` |
| `get_repo`     | Get a single repository              | `owner`, `repo`        | --                |
| `create_issue` | Create a new issue                   | `owner`, `repo`, `title` | `body`, `labels`  |
| `list_issues`  | List issues for a repository         | `owner`, `repo`        | `state`, `per_page` |
| `get_issue`    | Get a single issue                   | `owner`, `repo`, `number` | --              |

```python
from openclaw_sdk.connectors import GitHubConnector, ConnectorConfig

config = ConnectorConfig(api_key="ghp_xxx")
async with GitHubConnector(config) as gh:
    repos = await gh.list_repos(org="myorg")
    issue = await gh.get_issue("myorg", "myrepo", 42)
```

### Slack

Connector for the Slack Web API. Send messages, list channels and users, upload files.

**Auth:** Bot Token (`xoxb-...`) as `api_key`.

| Action          | Description                        | Required Params               | Optional Params |
|-----------------|------------------------------------|-------------------------------|-----------------|
| `send_message`  | Send a message to a channel        | `channel`, `text`             | --              |
| `list_channels` | List public channels               | --                            | `limit`         |
| `post_file`     | Upload a text file to a channel    | `channel`, `content`, `filename` | --           |
| `list_users`    | List all users in the workspace    | --                            | `limit`         |

```python
from openclaw_sdk.connectors import SlackConnector, ConnectorConfig

config = ConnectorConfig(api_key="xoxb-xxx")
async with SlackConnector(config) as slack:
    await slack.send_message("#general", "Deploy complete!")
    channels = await slack.list_channels(limit=50)
```

### Google Sheets

Connector for the Google Sheets API v4. Read, write, and list spreadsheet data.

**Auth:** OAuth2 access token as `api_key`.

| Action          | Description                          | Required Params                   | Optional Params |
|-----------------|--------------------------------------|-----------------------------------|-----------------|
| `get_values`    | Read cell values from a range        | `spreadsheet_id`, `range_`        | --              |
| `update_values` | Write values to a range              | `spreadsheet_id`, `range_`, `values` | --           |
| `list_sheets`   | List all sheets (tabs) in a spreadsheet | `spreadsheet_id`               | --              |

```python
from openclaw_sdk.connectors import GoogleSheetsConnector, ConnectorConfig

config = ConnectorConfig(api_key="ya29.xxx")
async with GoogleSheetsConnector(config) as sheets:
    data = await sheets.get_values("spreadsheet_id", "Sheet1!A1:C10")
    await sheets.update_values(
        "spreadsheet_id", "Sheet1!D1", [["Status"], ["Done"]]
    )
```

### Gmail

Connector for the Gmail API v1. Send, list, and read emails.

**Auth:** OAuth2 access token as `api_key`.

| Action          | Description                     | Required Params             | Optional Params         |
|-----------------|---------------------------------|-----------------------------|-------------------------|
| `send_email`    | Send an email via Gmail         | `to`, `subject`, `body`     | --                      |
| `list_messages` | List messages matching a query  | --                          | `query`, `max_results`  |
| `get_message`   | Get a single message by ID     | `message_id`                | --                      |

```python
from openclaw_sdk.connectors import GmailConnector, ConnectorConfig

config = ConnectorConfig(api_key="ya29.xxx")
async with GmailConnector(config) as gmail:
    await gmail.send_email("user@example.com", "Report", "See attached.")
    messages = await gmail.list_messages(query="from:alerts@company.com")
```

### Notion

Connector for the Notion API. Search, manage pages, and query databases.

**Auth:** Internal integration token as `api_key`.

| Action          | Description                                  | Required Params             | Optional Params |
|-----------------|----------------------------------------------|-----------------------------|-----------------|
| `search`        | Search across all pages and databases        | --                          | `query`         |
| `get_page`      | Retrieve a page by ID                        | `page_id`                   | --              |
| `create_page`   | Create a page inside a parent page or database | `parent_id`, `properties` | `is_database`   |
| `get_database`  | Retrieve a database by ID                    | `database_id`               | --              |

```python
from openclaw_sdk.connectors import NotionConnector, ConnectorConfig

config = ConnectorConfig(api_key="ntn_xxx")
async with NotionConnector(config) as notion:
    results = await notion.search("Project Plan")
    page = await notion.get_page("page-uuid-here")
```

### Jira

Connector for the Jira Cloud REST API v3. Search, create, and update issues.

**Auth:** Basic auth with email as `api_key` and API token as `api_secret`.
You must set `base_url` to your Atlassian instance.

| Action          | Description                   | Required Params                          | Optional Params  |
|-----------------|-------------------------------|------------------------------------------|------------------|
| `search_issues` | Search issues using JQL       | `jql`                                    | `max_results`    |
| `get_issue`     | Get a single issue by key     | `issue_key`                              | --               |
| `create_issue`  | Create a new issue            | `project_key`, `summary`, `issue_type`   | `description`    |
| `update_issue`  | Update an existing issue      | `issue_key`, `fields`                    | --               |

```python
from openclaw_sdk.connectors import JiraConnector, ConnectorConfig

config = ConnectorConfig(
    api_key="you@company.com",
    api_secret="ATATT3xFf...",
    base_url="https://yourorg.atlassian.net",
)
async with JiraConnector(config) as jira:
    issues = await jira.search_issues("project = DEV AND status = Open")
    await jira.create_issue("DEV", "Fix login bug", issue_type="Bug")
```

### Stripe

Connector for the Stripe REST API v1. Manage customers and charges.

**Auth:** Stripe secret key as `api_key`. Uses HTTP Basic auth internally.

| Action            | Description                  | Required Params | Optional Params   |
|-------------------|------------------------------|-----------------|-------------------|
| `list_customers`  | List Stripe customers        | --              | `limit`           |
| `create_customer` | Create a new customer        | --              | `email`, `name`   |
| `list_charges`    | List recent charges          | --              | `limit`           |
| `get_charge`      | Retrieve a single charge     | `charge_id`     | --                |

```python
from openclaw_sdk.connectors import StripeConnector, ConnectorConfig

config = ConnectorConfig(api_key="sk_test_xxx")
async with StripeConnector(config) as stripe:
    customers = await stripe.list_customers(limit=10)
    new_customer = await stripe.create_customer(
        email="alice@example.com", name="Alice"
    )
```

### HubSpot

Connector for the HubSpot CRM API v3. Manage contacts and deals.

**Auth:** Private app access token as `api_key`.

| Action           | Description               | Required Params | Optional Params    |
|------------------|---------------------------|-----------------|--------------------|
| `list_contacts`  | List CRM contacts         | --              | `limit`            |
| `create_contact` | Create a new contact      | `email`         | `properties`       |
| `list_deals`     | List CRM deals            | --              | `limit`            |
| `get_deal`       | Get a single deal by ID   | `deal_id`       | --                 |

```python
from openclaw_sdk.connectors import HubSpotConnector, ConnectorConfig

config = ConnectorConfig(api_key="pat-xxx")
async with HubSpotConnector(config) as hs:
    contacts = await hs.list_contacts(limit=20)
    await hs.create_contact(
        email="lead@example.com",
        properties={"firstname": "Bob", "lastname": "Smith"},
    )
```

### Salesforce

Connector for the Salesforce REST API (v58.0). Execute SOQL queries and manage sObject records.

**Auth:** OAuth access token as `api_key`. You must set `base_url` to your
Salesforce instance URL.

| Action          | Description                    | Required Params                  | Optional Params |
|-----------------|--------------------------------|----------------------------------|-----------------|
| `query`         | Execute a SOQL query           | `soql`                           | --              |
| `get_record`    | Get a single sObject record    | `sobject`, `record_id`           | --              |
| `create_record` | Create a new sObject record    | `sobject`, `fields`              | --              |
| `update_record` | Update an existing record      | `sobject`, `record_id`, `fields` | --              |

```python
from openclaw_sdk.connectors import SalesforceConnector, ConnectorConfig

config = ConnectorConfig(
    api_key="00Dxx0000...",
    base_url="https://yourorg.my.salesforce.com",
)
async with SalesforceConnector(config) as sf:
    result = await sf.query("SELECT Id, Name FROM Account LIMIT 10")
    await sf.create_record("Contact", {"LastName": "Doe", "Email": "doe@co.com"})
```

### Zendesk

Connector for the Zendesk Support API v2. Manage support tickets.

**Auth:** Email as `api_key` and Zendesk API token as `api_secret`. You must
set `base_url` to `https://yourorg.zendesk.com/api/v2`.

| Action          | Description                   | Required Params              | Optional Params       |
|-----------------|-------------------------------|------------------------------|-----------------------|
| `list_tickets`  | List support tickets          | --                           | `status`, `per_page`  |
| `get_ticket`    | Get a single ticket by ID     | `ticket_id`                  | --                    |
| `create_ticket` | Create a new support ticket   | `subject`, `description`     | `priority`            |
| `update_ticket` | Update an existing ticket     | `ticket_id`, `fields`        | --                    |

```python
from openclaw_sdk.connectors import ZendeskConnector, ConnectorConfig

config = ConnectorConfig(
    api_key="agent@company.com",
    api_secret="zd_token_xxx",
    base_url="https://myco.zendesk.com/api/v2",
)
async with ZendeskConnector(config) as zd:
    tickets = await zd.list_tickets(status="open")
    await zd.create_ticket(
        subject="App crashing on login",
        description="User reports...",
        priority="high",
    )
```

## Building a Custom Connector

You can create your own connector by extending the `Connector` ABC. Implement
`_build_headers()` and `list_actions()`, then add your action methods:

```python
from openclaw_sdk.connectors import Connector, ConnectorAction, ConnectorConfig

class MyAPIConnector(Connector):
    DEFAULT_BASE_URL = "https://api.myservice.com/v1"

    def _build_headers(self) -> dict[str, str]:
        headers = {**self._config.extra_headers}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        return headers

    def list_actions(self) -> list[ConnectorAction]:
        return [
            ConnectorAction(
                name="get_items",
                description="List all items",
                optional_params=["limit"],
            ),
        ]

    async def get_items(self, limit: int = 20) -> dict:
        client = self._ensure_connected()
        resp = await client.get("/items", params={"limit": limit})
        resp.raise_for_status()
        return resp.json()
```

!!! tip "Use `_ensure_connected()`"
    Always call `self._ensure_connected()` in your action methods. It returns
    the `httpx.AsyncClient` and raises `RuntimeError` if `connect()` has not
    been called yet.

## Authentication Patterns

Different connectors use different authentication schemes. Here is a summary:

| Connector        | Auth Scheme   | `api_key`                  | `api_secret`         | `base_url` Required? |
|------------------|---------------|----------------------------|----------------------|----------------------|
| GitHub           | Bearer token  | PAT or App token           | --                   | No                   |
| Slack            | Bearer token  | Bot token (`xoxb-...`)     | --                   | No                   |
| Google Sheets    | Bearer token  | OAuth2 access token        | --                   | No                   |
| Gmail            | Bearer token  | OAuth2 access token        | --                   | No                   |
| Notion           | Bearer token  | Integration token          | --                   | No                   |
| Jira             | Basic auth    | Email                      | API token            | Yes                  |
| Stripe           | Basic auth    | Secret key (`sk_...`)      | --                   | No                   |
| HubSpot          | Bearer token  | Private app token          | --                   | No                   |
| Salesforce       | Bearer token  | OAuth access token         | --                   | Yes                  |
| Zendesk          | Basic auth    | Email                      | API token            | Yes                  |

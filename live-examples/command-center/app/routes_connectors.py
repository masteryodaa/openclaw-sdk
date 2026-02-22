"""SaaS Connectors endpoints — list, connect, and execute connector actions."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from openclaw_sdk.connectors import (
    Connector,
    ConnectorConfig,
    GitHubConnector,
    SlackConnector,
    GoogleSheetsConnector,
    GmailConnector,
    NotionConnector,
    JiraConnector,
    StripeConnector,
    HubSpotConnector,
    SalesforceConnector,
    ZendeskConnector,
)

from . import gateway

router = APIRouter(prefix="/api/connectors", tags=["connectors"])

# Registry of available connector types
CONNECTOR_REGISTRY: dict[str, dict[str, Any]] = {
    "github": {
        "name": "GitHub",
        "description": "Repositories, issues, and pull requests",
        "class": GitHubConnector,
    },
    "slack": {
        "name": "Slack",
        "description": "Channels, messages, and notifications",
        "class": SlackConnector,
    },
    "google_sheets": {
        "name": "Google Sheets",
        "description": "Spreadsheet data and cell operations",
        "class": GoogleSheetsConnector,
    },
    "gmail": {
        "name": "Gmail",
        "description": "Email sending and inbox management",
        "class": GmailConnector,
    },
    "notion": {
        "name": "Notion",
        "description": "Pages, databases, and blocks",
        "class": NotionConnector,
    },
    "jira": {
        "name": "Jira",
        "description": "Issues, projects, and sprints",
        "class": JiraConnector,
    },
    "stripe": {
        "name": "Stripe",
        "description": "Payments, customers, and subscriptions",
        "class": StripeConnector,
    },
    "hubspot": {
        "name": "HubSpot",
        "description": "Contacts, deals, and CRM operations",
        "class": HubSpotConnector,
    },
    "salesforce": {
        "name": "Salesforce",
        "description": "Leads, opportunities, and accounts",
        "class": SalesforceConnector,
    },
    "zendesk": {
        "name": "Zendesk",
        "description": "Tickets, users, and support operations",
        "class": ZendeskConnector,
    },
}

# Active connector instances
_active_connectors: dict[str, Connector] = {}


# -- Request models --


class ConnectBody(BaseModel):
    api_key: str
    api_secret: str | None = None
    base_url: str | None = None


class ExecuteBody(BaseModel):
    action: str
    params: dict[str, Any] = {}


# -- Endpoints --


@router.get("")
async def list_connectors():
    """List available connector types and their connection status."""
    connectors = []
    for type_key, info in CONNECTOR_REGISTRY.items():
        connector_cls = info["class"]
        instance = _active_connectors.get(type_key)
        # Get actions from class with a dummy config
        try:
            dummy = connector_cls(ConnectorConfig())
            actions = [
                {
                    "name": a.name,
                    "description": a.description,
                    "required_params": a.required_params,
                    "optional_params": a.optional_params,
                }
                for a in dummy.list_actions()
            ]
        except Exception:
            actions = []
        connectors.append({
            "type": type_key,
            "name": info["name"],
            "description": info["description"],
            "connected": instance is not None,
            "actions": actions,
        })
    return {"connectors": connectors}


@router.post("/{connector_type}/connect")
async def connect_connector(connector_type: str, body: ConnectBody):
    """Create and connect a connector instance."""
    if connector_type not in CONNECTOR_REGISTRY:
        return {"error": f"Unknown connector type: {connector_type}"}

    # Close existing instance if any
    if connector_type in _active_connectors:
        try:
            await _active_connectors[connector_type].close()
        except Exception:
            pass

    connector_cls = CONNECTOR_REGISTRY[connector_type]["class"]
    config = ConnectorConfig(
        api_key=body.api_key,
        api_secret=body.api_secret,
        base_url=body.base_url,
    )
    instance = connector_cls(config)
    await instance.connect()
    _active_connectors[connector_type] = instance

    return {
        "connected": True,
        "type": connector_type,
        "name": CONNECTOR_REGISTRY[connector_type]["name"],
    }


@router.post("/{connector_type}/execute")
async def execute_action(connector_type: str, body: ExecuteBody):
    """Execute an action on a connected connector."""
    if connector_type not in CONNECTOR_REGISTRY:
        return {"error": f"Unknown connector type: {connector_type}"}
    if connector_type not in _active_connectors:
        return {"error": f"Connector '{connector_type}' is not connected. Connect it first."}

    instance = _active_connectors[connector_type]
    action_fn = getattr(instance, body.action, None)
    if action_fn is None or not callable(action_fn):
        return {"error": f"Action '{body.action}' not found on {connector_type} connector"}

    try:
        result = await action_fn(**body.params)
        return {
            "success": True,
            "action": body.action,
            "result": result,
        }
    except Exception as exc:
        return {
            "success": False,
            "action": body.action,
            "error": str(exc),
        }

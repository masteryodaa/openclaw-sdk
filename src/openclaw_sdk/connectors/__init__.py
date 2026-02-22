"""SaaS Connectors — real API integrations for 10 popular services."""

from __future__ import annotations

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

__all__ = [
    "Connector",
    "ConnectorConfig",
    "ConnectorAction",
    "GitHubConnector",
    "SlackConnector",
    "GoogleSheetsConnector",
    "GmailConnector",
    "NotionConnector",
    "JiraConnector",
    "StripeConnector",
    "HubSpotConnector",
    "SalesforceConnector",
    "ZendeskConnector",
]

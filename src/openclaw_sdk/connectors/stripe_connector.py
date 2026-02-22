"""Stripe connector — customers, charges, and payments."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from openclaw_sdk.connectors.base import Connector, ConnectorAction, ConnectorConfig

logger = structlog.get_logger(__name__)


class StripeConnector(Connector):
    """Connector for the Stripe REST API v1.

    Pass your Stripe secret key as ``api_key``.  Stripe uses Basic auth
    (key as username, empty password) and form-encoded request bodies.

    Usage::

        config = ConnectorConfig(api_key="sk_test_xxx")
        async with StripeConnector(config) as stripe:
            customers = await stripe.list_customers(limit=10)
    """

    DEFAULT_BASE_URL = "https://api.stripe.com/v1"

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            **self._config.extra_headers,
        }
        # Stripe uses Basic auth: api_key as username, empty password
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        return headers

    async def connect(self) -> None:
        """Open the HTTP client with Stripe-specific auth.

        Stripe uses the API key directly in the Authorization header via
        Bearer scheme, so we override connect only to set the appropriate
        base URL and headers.
        """
        base_url = self._config.base_url or self.DEFAULT_BASE_URL
        auth: httpx.BasicAuth | None = None
        if self._config.api_key:
            auth = httpx.BasicAuth(
                username=self._config.api_key, password=""
            )
        self._client = httpx.AsyncClient(
            base_url=base_url,
            auth=auth,
            headers={
                "Accept": "application/json",
                **self._config.extra_headers,
            },
            timeout=self._config.timeout,
        )
        logger.info(
            "connector.connected",
            connector="StripeConnector",
            base_url=base_url,
        )

    def list_actions(self) -> list[ConnectorAction]:
        return [
            ConnectorAction(
                name="list_customers",
                description="List Stripe customers",
                optional_params=["limit"],
            ),
            ConnectorAction(
                name="create_customer",
                description="Create a new Stripe customer",
                optional_params=["email", "name"],
            ),
            ConnectorAction(
                name="list_charges",
                description="List recent charges",
                optional_params=["limit"],
            ),
            ConnectorAction(
                name="get_charge",
                description="Retrieve a single charge",
                required_params=["charge_id"],
            ),
        ]

    async def list_customers(self, limit: int = 10) -> dict[str, Any]:
        """List Stripe customers.

        Args:
            limit: Maximum number of customers to return (1-100).

        Returns:
            Stripe list object with ``data`` array of customer objects.
        """
        client = self._ensure_connected()
        resp = await client.get("/customers", params={"limit": limit})
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def create_customer(
        self,
        email: str | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Create a new Stripe customer.

        Stripe uses form-encoded data (not JSON).

        Args:
            email: Customer email address.
            name: Customer display name.

        Returns:
            Created customer object.
        """
        client = self._ensure_connected()
        data: dict[str, str] = {}
        if email:
            data["email"] = email
        if name:
            data["name"] = name
        resp = await client.post("/customers", data=data)
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def list_charges(self, limit: int = 10) -> dict[str, Any]:
        """List recent charges.

        Args:
            limit: Maximum number of charges to return (1-100).

        Returns:
            Stripe list object with ``data`` array of charge objects.
        """
        client = self._ensure_connected()
        resp = await client.get("/charges", params={"limit": limit})
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def get_charge(self, charge_id: str) -> dict[str, Any]:
        """Retrieve a single charge by ID.

        Args:
            charge_id: The Stripe charge ID (e.g. ``"ch_xxx"``).

        Returns:
            Charge object.
        """
        client = self._ensure_connected()
        resp = await client.get(f"/charges/{charge_id}")
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

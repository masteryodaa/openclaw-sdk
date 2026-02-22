"""Supabase REST API data source using ``httpx``.

Uses the PostgREST-compatible REST endpoint that every Supabase project
exposes.  No additional dependencies beyond ``httpx`` (already a core
SDK dependency).
"""

from __future__ import annotations

import time
from typing import Any

import httpx
import structlog

from openclaw_sdk.data.base import DataSource, QueryResult, TableInfo

logger = structlog.get_logger(__name__)


class SupabaseDataSource(DataSource):
    """Supabase REST API data source.

    Queries are expressed as either:

    * A bare table name (e.g. ``"users"``) for a simple ``SELECT *``.
    * An ``"rpc:<function_name>"`` prefix to call a Postgres RPC function
      via the ``/rpc/`` endpoint.

    Args:
        url: Supabase project URL (e.g.
            ``"https://xyzcompany.supabase.co"``).
        api_key: Supabase ``anon`` or ``service_role`` API key.
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        url: str,
        api_key: str,
        *,
        timeout: float = 30.0,
    ) -> None:
        self._url = url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    # -- lifecycle ----------------------------------------------------------

    async def connect(self) -> None:
        """Open an ``httpx.AsyncClient`` pointed at the Supabase REST API."""
        self._client = httpx.AsyncClient(
            base_url=f"{self._url}/rest/v1",
            headers={
                "apikey": self._api_key,
                "Authorization": f"Bearer {self._api_key}",
                "Prefer": "return=representation",
            },
            timeout=self._timeout,
        )
        logger.info("supabase.connected", url=self._url)

    async def close(self) -> None:
        """Close the ``httpx.AsyncClient``."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("supabase.closed")

    # -- query execution ----------------------------------------------------

    async def execute(
        self, query: str, params: list[Any] | None = None
    ) -> QueryResult:
        """Execute a table query or RPC call.

        If *query* starts with ``"rpc:"``, the remainder is used as the
        function name and *params* (if any) are passed as JSON body to
        ``POST /rpc/<function_name>``.

        Otherwise *query* is treated as a table name and a
        ``GET /<table>`` request is made (PostgREST ``SELECT *``).

        Raises:
            RuntimeError: If not connected.
            httpx.HTTPStatusError: If the Supabase API returns a non-2xx response.
        """
        if self._client is None:
            raise RuntimeError("Not connected")

        t0 = time.monotonic()

        if query.startswith("rpc:"):
            func_name = query[4:]
            resp = await self._client.post(
                f"/rpc/{func_name}", json=params or {}
            )
        else:
            resp = await self._client.get(f"/{query}")

        resp.raise_for_status()
        data = resp.json()
        elapsed = (time.monotonic() - t0) * 1000

        if isinstance(data, list) and data:
            columns = list(data[0].keys())
            rows = [list(item.values()) for item in data]
        else:
            columns = []
            rows = []

        return QueryResult(
            columns=columns,
            rows=rows,
            row_count=len(rows),
            execution_time_ms=round(elapsed, 2),
        )

    # -- schema introspection -----------------------------------------------

    async def list_tables(self) -> list[str]:
        """Return an empty list.

        The Supabase REST API does not expose a table-listing endpoint.
        Use the SQL editor or ``pg_catalog`` via RPC for introspection.
        """
        return []

    async def describe_table(self, table: str) -> TableInfo:
        """Return a minimal :class:`TableInfo` with no column metadata.

        Full introspection requires querying ``information_schema`` via
        an RPC function.
        """
        return TableInfo(name=table)

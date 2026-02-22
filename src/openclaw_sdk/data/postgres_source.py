"""PostgreSQL data source using ``asyncpg`` (optional dependency).

Install with::

    pip install openclaw-sdk[data-postgres]
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from openclaw_sdk.data.base import ColumnInfo, DataSource, QueryResult, TableInfo

logger = structlog.get_logger(__name__)


class PostgresDataSource(DataSource):
    """PostgreSQL data source backed by ``asyncpg``.

    Requires the ``asyncpg`` package.  If it is not installed, the
    constructor raises :class:`ImportError` with installation instructions.

    Args:
        dsn: PostgreSQL connection string (e.g.
            ``"postgresql://user:pass@host:5432/db"``).
        min_pool_size: Minimum number of connections in the pool.
        max_pool_size: Maximum number of connections in the pool.
    """

    def __init__(
        self,
        dsn: str,
        *,
        min_pool_size: int = 2,
        max_pool_size: int = 10,
    ) -> None:
        try:
            import asyncpg  # noqa: F401
        except ImportError:
            raise ImportError(
                "asyncpg required for PostgresDataSource. "
                "Install with: pip install openclaw-sdk[data-postgres]"
            ) from None
        self._dsn = dsn
        self._min_pool_size = min_pool_size
        self._max_pool_size = max_pool_size
        self._pool: Any = None  # asyncpg.Pool

    # -- lifecycle ----------------------------------------------------------

    async def connect(self) -> None:
        """Create a connection pool to the PostgreSQL server."""
        import asyncpg

        self._pool = await asyncpg.create_pool(
            self._dsn,
            min_size=self._min_pool_size,
            max_size=self._max_pool_size,
        )
        logger.info("postgres.connected", dsn=self._dsn)

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("postgres.closed")

    # -- query execution ----------------------------------------------------

    async def execute(
        self, query: str, params: list[Any] | None = None
    ) -> QueryResult:
        """Execute *query* with optional positional *params*.

        Raises:
            RuntimeError: If not connected.
        """
        if self._pool is None:
            raise RuntimeError("Not connected")
        t0 = time.monotonic()
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *(params or []))
            elapsed = (time.monotonic() - t0) * 1000
            if rows:
                columns = list(rows[0].keys())
                data = [list(r.values()) for r in rows]
            else:
                columns = []
                data = []
            return QueryResult(
                columns=columns,
                rows=data,
                row_count=len(data),
                execution_time_ms=round(elapsed, 2),
            )

    # -- schema introspection -----------------------------------------------

    async def list_tables(self) -> list[str]:
        """Return sorted list of tables in the ``public`` schema."""
        result = await self.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name"
        )
        return [row[0] for row in result.rows]

    async def describe_table(self, table: str) -> TableInfo:
        """Return column metadata for *table*."""
        result = await self.execute(
            "SELECT column_name, data_type, is_nullable, "
            "CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END "
            "AS is_pk "
            "FROM information_schema.columns c "
            "LEFT JOIN ("
            "  SELECT ku.column_name "
            "  FROM information_schema.table_constraints tc "
            "  JOIN information_schema.key_column_usage ku "
            "    ON tc.constraint_name = ku.constraint_name "
            "  WHERE tc.table_name = $1 "
            "    AND tc.constraint_type = 'PRIMARY KEY'"
            ") pk ON c.column_name = pk.column_name "
            "WHERE c.table_name = $1 "
            "ORDER BY c.ordinal_position",
            [table],
        )
        columns = [
            ColumnInfo(
                name=row[0],
                data_type=row[1],
                nullable=row[2] == "YES",
                primary_key=bool(row[3]),
            )
            for row in result.rows
        ]
        return TableInfo(name=table, columns=columns)

"""MySQL data source using ``aiomysql`` (optional dependency).

Install with::

    pip install openclaw-sdk[data-mysql]
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from openclaw_sdk.data.base import ColumnInfo, DataSource, QueryResult, TableInfo

logger = structlog.get_logger(__name__)


class MySQLDataSource(DataSource):
    """MySQL data source backed by ``aiomysql``.

    Requires the ``aiomysql`` package.  If it is not installed, the
    constructor raises :class:`ImportError` with installation instructions.

    Args:
        host: Database server hostname.
        port: Database server port (default 3306).
        user: Database user.
        password: Database password.
        database: Database name.
        min_pool_size: Minimum number of connections in the pool.
        max_pool_size: Maximum number of connections in the pool.
    """

    def __init__(
        self,
        host: str,
        *,
        port: int = 3306,
        user: str = "root",
        password: str = "",
        database: str = "",
        min_pool_size: int = 1,
        max_pool_size: int = 10,
    ) -> None:
        try:
            import aiomysql  # noqa: F401
        except ImportError:
            raise ImportError(
                "aiomysql required for MySQLDataSource. "
                "Install with: pip install openclaw-sdk[data-mysql]"
            ) from None
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._database = database
        self._min_pool_size = min_pool_size
        self._max_pool_size = max_pool_size
        self._pool: Any = None  # aiomysql.Pool

    # -- lifecycle ----------------------------------------------------------

    async def connect(self) -> None:
        """Create a connection pool to the MySQL server."""
        import aiomysql

        self._pool = await aiomysql.create_pool(
            host=self._host,
            port=self._port,
            user=self._user,
            password=self._password,
            db=self._database,
            minsize=self._min_pool_size,
            maxsize=self._max_pool_size,
        )
        logger.info(
            "mysql.connected",
            host=self._host,
            port=self._port,
            database=self._database,
        )

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool is not None:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
            logger.info("mysql.closed")

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
            async with conn.cursor() as cursor:
                await cursor.execute(query, params or [])
                columns = (
                    [desc[0] for desc in cursor.description]
                    if cursor.description
                    else []
                )
                rows = await cursor.fetchall()
                elapsed = (time.monotonic() - t0) * 1000
                return QueryResult(
                    columns=columns,
                    rows=[list(row) for row in rows],
                    row_count=len(rows),
                    execution_time_ms=round(elapsed, 2),
                )

    # -- schema introspection -----------------------------------------------

    async def list_tables(self) -> list[str]:
        """Return sorted list of tables in the current database."""
        result = await self.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = DATABASE() ORDER BY table_name"
        )
        return [row[0] for row in result.rows]

    async def describe_table(self, table: str) -> TableInfo:
        """Return column metadata for *table*."""
        result = await self.execute(
            "SELECT column_name, data_type, is_nullable, column_key "
            "FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = %s "
            "ORDER BY ordinal_position",
            [table],
        )
        columns = [
            ColumnInfo(
                name=row[0],
                data_type=row[1],
                nullable=row[2] == "YES",
                primary_key=row[3] == "PRI",
            )
            for row in result.rows
        ]
        return TableInfo(name=table, columns=columns)

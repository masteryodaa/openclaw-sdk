"""SQLite data source using stdlib ``sqlite3`` + ``asyncio.to_thread``.

Zero external dependencies -- uses Python's built-in :mod:`sqlite3` module.
All blocking I/O is delegated to a thread via :func:`asyncio.to_thread` so
the event loop is never blocked.
"""

from __future__ import annotations

import asyncio
import sqlite3
import time
from typing import Any

import structlog

from openclaw_sdk.data.base import ColumnInfo, DataSource, QueryResult, TableInfo

logger = structlog.get_logger(__name__)


class SQLiteDataSource(DataSource):
    """SQLite data source with async wrappers around :mod:`sqlite3`.

    Args:
        database: Path to the SQLite database file, or ``":memory:"``
            for an in-memory database.
        read_only: When ``True``, only ``SELECT`` and ``PRAGMA`` statements
            are allowed.  File-backed databases are opened with the
            ``?mode=ro`` URI flag.
    """

    def __init__(
        self, database: str = ":memory:", read_only: bool = False
    ) -> None:
        self._database = database
        self._read_only = read_only
        self._conn: sqlite3.Connection | None = None

    # -- lifecycle ----------------------------------------------------------

    async def connect(self) -> None:
        """Open the SQLite connection in a worker thread."""

        def _connect() -> sqlite3.Connection:
            if self._read_only and self._database != ":memory:":
                uri = f"file:{self._database}?mode=ro"
                return sqlite3.connect(
                    uri, uri=True, check_same_thread=False
                )
            return sqlite3.connect(
                self._database, check_same_thread=False
            )

        self._conn = await asyncio.to_thread(_connect)
        logger.info(
            "sqlite.connected",
            database=self._database,
            read_only=self._read_only,
        )

    async def close(self) -> None:
        """Close the SQLite connection in a worker thread."""
        if self._conn is not None:
            await asyncio.to_thread(self._conn.close)
            self._conn = None
            logger.info("sqlite.closed", database=self._database)

    # -- query execution ----------------------------------------------------

    async def execute(
        self, query: str, params: list[Any] | None = None
    ) -> QueryResult:
        """Execute *query* with optional *params*.

        In read-only mode, only ``SELECT`` and ``PRAGMA`` statements are
        permitted; any other statement raises :class:`PermissionError`.

        Raises:
            RuntimeError: If not connected.
            PermissionError: If a write statement is attempted in read-only mode.
        """
        if self._conn is None:
            raise RuntimeError("Not connected")

        if self._read_only:
            stripped = query.strip().upper()
            if not stripped.startswith("SELECT") and not stripped.startswith(
                "PRAGMA"
            ):
                raise PermissionError(
                    "Read-only mode: only SELECT and PRAGMA allowed"
                )

        conn = self._conn  # capture for closure

        def _exec() -> QueryResult:
            t0 = time.monotonic()
            cursor = conn.execute(query, params or [])
            columns = (
                [desc[0] for desc in cursor.description]
                if cursor.description
                else []
            )
            rows = cursor.fetchall()
            elapsed = (time.monotonic() - t0) * 1000
            conn.commit()
            return QueryResult(
                columns=columns,
                rows=[list(row) for row in rows],
                row_count=len(rows),
                execution_time_ms=round(elapsed, 2),
            )

        return await asyncio.to_thread(_exec)

    # -- schema introspection -----------------------------------------------

    async def list_tables(self) -> list[str]:
        """Return sorted list of user tables in the database."""
        result = await self.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [row[0] for row in result.rows]

    async def describe_table(self, table: str) -> TableInfo:
        """Return column metadata and row count for *table*.

        Uses ``PRAGMA table_info`` to introspect columns.
        """
        result = await self.execute(f"PRAGMA table_info({table})")
        columns = [
            ColumnInfo(
                name=row[1],
                data_type=row[2] or "TEXT",
                nullable=not bool(row[3]),
                primary_key=bool(row[5]),
            )
            for row in result.rows
        ]
        count_result = await self.execute(
            f"SELECT COUNT(*) FROM {table}"  # noqa: S608
        )
        row_count = count_result.rows[0][0] if count_result.rows else 0
        return TableInfo(name=table, columns=columns, row_count=row_count)

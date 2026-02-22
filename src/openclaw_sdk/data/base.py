"""Data source abstraction layer.

Provides :class:`DataSource` (abstract base), :class:`QueryResult`,
:class:`TableInfo`, :class:`ColumnInfo` (Pydantic models), and
:class:`DataSourceRegistry` for managing named data source instances.
"""

from __future__ import annotations

import structlog
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ColumnInfo(BaseModel):
    """Metadata for a single database column."""

    name: str
    data_type: str
    nullable: bool = True
    primary_key: bool = False


class TableInfo(BaseModel):
    """Metadata for a database table including its columns."""

    name: str
    columns: list[ColumnInfo] = Field(default_factory=list)
    row_count: int | None = None


class QueryResult(BaseModel):
    """Result of a database query execution.

    Attributes:
        columns: Column names from the result set.
        rows: List of rows, each row is a list of values.
        row_count: Number of rows returned.
        execution_time_ms: Wall-clock execution time in milliseconds.
    """

    columns: list[str] = Field(default_factory=list)
    rows: list[list[Any]] = Field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float = 0.0


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------


class DataSource(ABC):
    """Abstract base for database data sources.

    Subclasses must implement :meth:`connect`, :meth:`close`,
    :meth:`execute`, :meth:`list_tables`, and :meth:`describe_table`.

    Convenience methods :meth:`fetch_one` and :meth:`fetch_all` are
    provided on top of :meth:`execute`.  The class also supports the
    async context manager protocol (``async with``).
    """

    @abstractmethod
    async def connect(self) -> None:
        """Open the connection / connection pool."""

    @abstractmethod
    async def close(self) -> None:
        """Close the connection / connection pool."""

    @abstractmethod
    async def execute(
        self, query: str, params: list[Any] | None = None
    ) -> QueryResult:
        """Execute *query* with optional positional *params*.

        Returns:
            A :class:`QueryResult` with columns, rows, and timing info.
        """

    @abstractmethod
    async def list_tables(self) -> list[str]:
        """Return a sorted list of table names in the data source."""

    @abstractmethod
    async def describe_table(self, table: str) -> TableInfo:
        """Return column metadata and optional row count for *table*."""

    # -- convenience helpers ------------------------------------------------

    async def fetch_one(
        self, query: str, params: list[Any] | None = None
    ) -> dict[str, Any] | None:
        """Execute *query* and return the first row as a dict, or ``None``.

        Useful for lookups by primary key or queries expected to return a
        single row.
        """
        result = await self.execute(query, params)
        if not result.rows:
            return None
        return dict(zip(result.columns, result.rows[0]))

    async def fetch_all(
        self, query: str, params: list[Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute *query* and return all rows as a list of dicts."""
        result = await self.execute(query, params)
        return [dict(zip(result.columns, row)) for row in result.rows]

    # -- async context manager ----------------------------------------------

    async def __aenter__(self) -> DataSource:
        await self.connect()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class DataSourceRegistry:
    """Registry for named :class:`DataSource` instances.

    Allows centralised management of multiple data sources so they can be
    looked up by name and closed together at shutdown.
    """

    def __init__(self) -> None:
        self._sources: dict[str, DataSource] = {}

    def register(self, name: str, source: DataSource) -> None:
        """Register *source* under *name*.

        Raises:
            ValueError: If *name* is already registered.
        """
        if name in self._sources:
            raise ValueError(f"Data source '{name}' is already registered")
        self._sources[name] = source
        logger.info("data_source.registered", name=name)

    def get(self, name: str) -> DataSource:
        """Return the data source registered under *name*.

        Raises:
            KeyError: If *name* is not registered.
        """
        try:
            return self._sources[name]
        except KeyError:
            raise KeyError(f"Data source '{name}' not found") from None

    def list_sources(self) -> list[str]:
        """Return sorted list of registered data source names."""
        return sorted(self._sources.keys())

    async def close_all(self) -> None:
        """Close every registered data source and clear the registry."""
        for name, source in self._sources.items():
            try:
                await source.close()
                logger.info("data_source.closed", name=name)
            except Exception:
                logger.exception("data_source.close_error", name=name)
        self._sources.clear()

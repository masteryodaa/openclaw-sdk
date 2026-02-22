"""Data source abstraction layer for database access.

Provides a unified async interface for querying databases (SQLite,
PostgreSQL, MySQL) and REST APIs (Supabase).

Core classes (always available):

- :class:`DataSource` -- abstract base class
- :class:`QueryResult`, :class:`TableInfo`, :class:`ColumnInfo` -- result models
- :class:`DataSourceRegistry` -- named-instance registry
- :class:`SQLiteDataSource` -- zero-dependency SQLite backend

Optional backends (require extra packages):

- :class:`PostgresDataSource` -- ``pip install openclaw-sdk[data-postgres]``
- :class:`MySQLDataSource` -- ``pip install openclaw-sdk[data-mysql]``
- :class:`SupabaseDataSource` -- uses ``httpx`` (no extra dep)
"""

from __future__ import annotations

from openclaw_sdk.data.base import (
    ColumnInfo,
    DataSource,
    DataSourceRegistry,
    QueryResult,
    TableInfo,
)
from openclaw_sdk.data.sqlite_source import SQLiteDataSource
from openclaw_sdk.data.supabase_source import SupabaseDataSource

__all__ = [
    "ColumnInfo",
    "DataSource",
    "DataSourceRegistry",
    "QueryResult",
    "SQLiteDataSource",
    "SupabaseDataSource",
    "TableInfo",
]

# -- conditional imports for optional backends ------------------------------

try:
    from openclaw_sdk.data.postgres_source import PostgresDataSource  # noqa: F401

    __all__.append("PostgresDataSource")
except ImportError:
    pass

try:
    from openclaw_sdk.data.mysql_source import MySQLDataSource  # noqa: F401

    __all__.append("MySQLDataSource")
except ImportError:
    pass

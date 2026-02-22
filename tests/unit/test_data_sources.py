"""Tests for data/ — DataSource abstraction layer."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from openclaw_sdk.data.base import (
    ColumnInfo,
    DataSourceRegistry,
    QueryResult,
    TableInfo,
)
from openclaw_sdk.data.sqlite_source import SQLiteDataSource
from openclaw_sdk.data.supabase_source import SupabaseDataSource


# ---------------------------------------------------------------------------
# Pydantic model tests
# ---------------------------------------------------------------------------


class TestQueryResultModel:
    def test_defaults(self) -> None:
        result = QueryResult()
        assert result.columns == []
        assert result.rows == []
        assert result.row_count == 0
        assert result.execution_time_ms == 0.0

    def test_with_data(self) -> None:
        result = QueryResult(
            columns=["id", "name"],
            rows=[[1, "Alice"], [2, "Bob"]],
            row_count=2,
            execution_time_ms=1.23,
        )
        assert result.columns == ["id", "name"]
        assert len(result.rows) == 2
        assert result.row_count == 2
        assert result.execution_time_ms == 1.23


class TestTableInfoModel:
    def test_defaults(self) -> None:
        info = TableInfo(name="users")
        assert info.name == "users"
        assert info.columns == []
        assert info.row_count is None

    def test_with_columns(self) -> None:
        cols = [
            ColumnInfo(name="id", data_type="INTEGER", primary_key=True),
            ColumnInfo(name="email", data_type="TEXT", nullable=False),
        ]
        info = TableInfo(name="users", columns=cols, row_count=42)
        assert len(info.columns) == 2
        assert info.row_count == 42


class TestColumnInfoModel:
    def test_defaults(self) -> None:
        col = ColumnInfo(name="age", data_type="INTEGER")
        assert col.name == "age"
        assert col.data_type == "INTEGER"
        assert col.nullable is True
        assert col.primary_key is False

    def test_primary_key(self) -> None:
        col = ColumnInfo(
            name="id",
            data_type="INTEGER",
            nullable=False,
            primary_key=True,
        )
        assert col.primary_key is True
        assert col.nullable is False


# ---------------------------------------------------------------------------
# SQLiteDataSource tests
# ---------------------------------------------------------------------------


class TestSQLiteConnectClose:
    async def test_connect_and_close(self) -> None:
        ds = SQLiteDataSource(":memory:")
        await ds.connect()
        assert ds._conn is not None
        await ds.close()
        assert ds._conn is None

    async def test_close_when_not_connected(self) -> None:
        ds = SQLiteDataSource(":memory:")
        # Closing when not connected should not raise
        await ds.close()
        assert ds._conn is None


class TestSQLiteExecuteSelect:
    async def test_simple_select(self) -> None:
        ds = SQLiteDataSource(":memory:")
        await ds.connect()
        try:
            result = await ds.execute("SELECT 1 AS val, 'hello' AS msg")
            assert result.columns == ["val", "msg"]
            assert result.rows == [[1, "hello"]]
            assert result.row_count == 1
            assert result.execution_time_ms >= 0
        finally:
            await ds.close()


class TestSQLiteExecuteInsertSelect:
    async def test_insert_and_select(self) -> None:
        ds = SQLiteDataSource(":memory:")
        await ds.connect()
        try:
            await ds.execute(
                "CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT)"
            )
            await ds.execute(
                "INSERT INTO items (id, name) VALUES (1, 'Widget')"
            )
            await ds.execute(
                "INSERT INTO items (id, name) VALUES (2, 'Gadget')"
            )
            result = await ds.execute(
                "SELECT id, name FROM items ORDER BY id"
            )
            assert result.columns == ["id", "name"]
            assert result.rows == [[1, "Widget"], [2, "Gadget"]]
            assert result.row_count == 2
        finally:
            await ds.close()


class TestSQLiteListTables:
    async def test_list_tables(self) -> None:
        ds = SQLiteDataSource(":memory:")
        await ds.connect()
        try:
            await ds.execute("CREATE TABLE alpha (id INTEGER)")
            await ds.execute("CREATE TABLE beta (id INTEGER)")
            tables = await ds.list_tables()
            assert tables == ["alpha", "beta"]
        finally:
            await ds.close()

    async def test_list_tables_empty(self) -> None:
        ds = SQLiteDataSource(":memory:")
        await ds.connect()
        try:
            tables = await ds.list_tables()
            assert tables == []
        finally:
            await ds.close()


class TestSQLiteDescribeTable:
    async def test_describe(self) -> None:
        ds = SQLiteDataSource(":memory:")
        await ds.connect()
        try:
            await ds.execute(
                "CREATE TABLE users ("
                "  id INTEGER PRIMARY KEY,"
                "  email TEXT NOT NULL,"
                "  age INTEGER"
                ")"
            )
            await ds.execute(
                "INSERT INTO users VALUES (1, 'a@b.com', 25)"
            )
            info = await ds.describe_table("users")
            assert info.name == "users"
            assert info.row_count == 1
            assert len(info.columns) == 3

            id_col = info.columns[0]
            assert id_col.name == "id"
            assert id_col.data_type == "INTEGER"
            assert id_col.primary_key is True

            email_col = info.columns[1]
            assert email_col.name == "email"
            assert email_col.nullable is False

            age_col = info.columns[2]
            assert age_col.name == "age"
            assert age_col.nullable is True
        finally:
            await ds.close()


class TestSQLiteFetchOne:
    async def test_fetch_one_found(self) -> None:
        ds = SQLiteDataSource(":memory:")
        await ds.connect()
        try:
            await ds.execute(
                "CREATE TABLE kv (key TEXT PRIMARY KEY, val TEXT)"
            )
            await ds.execute("INSERT INTO kv VALUES ('a', '1')")
            row = await ds.fetch_one("SELECT key, val FROM kv WHERE key='a'")
            assert row == {"key": "a", "val": "1"}
        finally:
            await ds.close()

    async def test_fetch_one_not_found(self) -> None:
        ds = SQLiteDataSource(":memory:")
        await ds.connect()
        try:
            await ds.execute(
                "CREATE TABLE kv (key TEXT PRIMARY KEY, val TEXT)"
            )
            row = await ds.fetch_one(
                "SELECT key, val FROM kv WHERE key='missing'"
            )
            assert row is None
        finally:
            await ds.close()


class TestSQLiteFetchAll:
    async def test_fetch_all(self) -> None:
        ds = SQLiteDataSource(":memory:")
        await ds.connect()
        try:
            await ds.execute("CREATE TABLE nums (n INTEGER)")
            await ds.execute("INSERT INTO nums VALUES (10)")
            await ds.execute("INSERT INTO nums VALUES (20)")
            rows = await ds.fetch_all("SELECT n FROM nums ORDER BY n")
            assert rows == [{"n": 10}, {"n": 20}]
        finally:
            await ds.close()

    async def test_fetch_all_empty(self) -> None:
        ds = SQLiteDataSource(":memory:")
        await ds.connect()
        try:
            await ds.execute("CREATE TABLE empty_tbl (n INTEGER)")
            rows = await ds.fetch_all("SELECT n FROM empty_tbl")
            assert rows == []
        finally:
            await ds.close()


class TestSQLiteReadOnly:
    async def test_blocks_writes(self) -> None:
        ds = SQLiteDataSource(":memory:", read_only=True)
        await ds.connect()
        try:
            with pytest.raises(PermissionError, match="Read-only mode"):
                await ds.execute("CREATE TABLE x (id INTEGER)")
        finally:
            await ds.close()

    async def test_blocks_insert(self) -> None:
        ds = SQLiteDataSource(":memory:", read_only=True)
        await ds.connect()
        try:
            with pytest.raises(PermissionError, match="Read-only mode"):
                await ds.execute("INSERT INTO x VALUES (1)")
        finally:
            await ds.close()

    async def test_allows_select(self) -> None:
        ds = SQLiteDataSource(":memory:", read_only=True)
        await ds.connect()
        try:
            result = await ds.execute("SELECT 42 AS answer")
            assert result.rows == [[42]]
        finally:
            await ds.close()

    async def test_allows_pragma(self) -> None:
        ds = SQLiteDataSource(":memory:", read_only=True)
        await ds.connect()
        try:
            result = await ds.execute("PRAGMA database_list")
            assert result.row_count >= 1
        finally:
            await ds.close()


class TestSQLiteContextManager:
    async def test_context_manager(self) -> None:
        async with SQLiteDataSource(":memory:") as ds:
            result = await ds.execute("SELECT 1 AS one")
            assert result.rows == [[1]]
        # After exit, connection should be closed
        assert ds._conn is None


class TestSQLiteNotConnectedRaises:
    async def test_execute_raises(self) -> None:
        ds = SQLiteDataSource(":memory:")
        with pytest.raises(RuntimeError, match="Not connected"):
            await ds.execute("SELECT 1")


class TestSQLiteParameterizedQuery:
    async def test_parameterized(self) -> None:
        async with SQLiteDataSource(":memory:") as ds:
            await ds.execute(
                "CREATE TABLE products (id INTEGER, name TEXT, price REAL)"
            )
            await ds.execute(
                "INSERT INTO products VALUES (?, ?, ?)",
                [1, "Widget", 9.99],
            )
            await ds.execute(
                "INSERT INTO products VALUES (?, ?, ?)",
                [2, "Gadget", 19.99],
            )
            result = await ds.execute(
                "SELECT name, price FROM products WHERE price > ?",
                [10.0],
            )
            assert result.row_count == 1
            assert result.rows[0][0] == "Gadget"
            assert result.rows[0][1] == 19.99


# ---------------------------------------------------------------------------
# DataSourceRegistry tests
# ---------------------------------------------------------------------------


class TestRegistryRegisterGet:
    async def test_register_and_get(self) -> None:
        registry = DataSourceRegistry()
        ds = SQLiteDataSource(":memory:")
        registry.register("mydb", ds)
        assert registry.get("mydb") is ds

    def test_duplicate_register_raises(self) -> None:
        registry = DataSourceRegistry()
        ds = SQLiteDataSource(":memory:")
        registry.register("mydb", ds)
        with pytest.raises(ValueError, match="already registered"):
            registry.register("mydb", ds)

    def test_get_missing_raises(self) -> None:
        registry = DataSourceRegistry()
        with pytest.raises(KeyError, match="not found"):
            registry.get("nonexistent")


class TestRegistryListSources:
    def test_list_sources_empty(self) -> None:
        registry = DataSourceRegistry()
        assert registry.list_sources() == []

    def test_list_sources_sorted(self) -> None:
        registry = DataSourceRegistry()
        registry.register("zebra", SQLiteDataSource(":memory:"))
        registry.register("alpha", SQLiteDataSource(":memory:"))
        registry.register("middle", SQLiteDataSource(":memory:"))
        assert registry.list_sources() == ["alpha", "middle", "zebra"]


class TestRegistryCloseAll:
    async def test_close_all(self) -> None:
        registry = DataSourceRegistry()
        ds1 = SQLiteDataSource(":memory:")
        ds2 = SQLiteDataSource(":memory:")
        await ds1.connect()
        await ds2.connect()
        registry.register("db1", ds1)
        registry.register("db2", ds2)

        await registry.close_all()

        assert ds1._conn is None
        assert ds2._conn is None
        assert registry.list_sources() == []

    async def test_close_all_handles_errors(self) -> None:
        """close_all should not raise even if a source fails to close."""
        registry = DataSourceRegistry()
        ds = SQLiteDataSource(":memory:")
        await ds.connect()
        registry.register("broken", ds)

        # Patch close to raise
        async def _bad_close() -> None:
            raise RuntimeError("close failed")

        ds.close = _bad_close  # type: ignore[assignment]

        # Should not raise
        await registry.close_all()
        assert registry.list_sources() == []


# ---------------------------------------------------------------------------
# PostgresDataSource import error test
# ---------------------------------------------------------------------------


class TestPostgresImportError:
    def test_import_error_message(self) -> None:
        # Temporarily hide asyncpg if present
        with patch.dict(sys.modules, {"asyncpg": None}):
            # Re-import to trigger the ImportError path
            from openclaw_sdk.data import postgres_source

            # Force reload to hit the import guard
            import importlib

            importlib.reload(postgres_source)

            with pytest.raises(
                ImportError, match="asyncpg required"
            ):
                postgres_source.PostgresDataSource(
                    dsn="postgresql://localhost/test"
                )


# ---------------------------------------------------------------------------
# MySQLDataSource import error test
# ---------------------------------------------------------------------------


class TestMySQLImportError:
    def test_import_error_message(self) -> None:
        with patch.dict(sys.modules, {"aiomysql": None}):
            from openclaw_sdk.data import mysql_source

            import importlib

            importlib.reload(mysql_source)

            with pytest.raises(
                ImportError, match="aiomysql required"
            ):
                mysql_source.MySQLDataSource(host="localhost")


# ---------------------------------------------------------------------------
# SupabaseDataSource tests (httpx mocked)
# ---------------------------------------------------------------------------


class TestSupabaseMocked:
    async def test_table_query(self) -> None:
        ds = SupabaseDataSource(
            url="https://test.supabase.co", api_key="test-key"
        )
        await ds.connect()
        assert ds._client is not None

        try:
            mock_response = httpx.Response(
                200,
                json=[
                    {"id": 1, "name": "Alice"},
                    {"id": 2, "name": "Bob"},
                ],
                request=httpx.Request("GET", "https://test.supabase.co/rest/v1/users"),
            )

            with patch.object(
                ds._client, "get", new_callable=AsyncMock, return_value=mock_response
            ):
                result = await ds.execute("users")
                assert result.columns == ["id", "name"]
                assert result.row_count == 2
                assert result.rows[0] == [1, "Alice"]
                assert result.rows[1] == [2, "Bob"]
        finally:
            await ds.close()

    async def test_rpc_query(self) -> None:
        ds = SupabaseDataSource(
            url="https://test.supabase.co", api_key="test-key"
        )
        await ds.connect()
        assert ds._client is not None

        try:
            mock_response = httpx.Response(
                200,
                json=[{"total": 42}],
                request=httpx.Request(
                    "POST",
                    "https://test.supabase.co/rest/v1/rpc/get_total",
                ),
            )

            with patch.object(
                ds._client, "post", new_callable=AsyncMock, return_value=mock_response
            ):
                result = await ds.execute("rpc:get_total")
                assert result.columns == ["total"]
                assert result.rows == [[42]]
        finally:
            await ds.close()

    async def test_empty_response(self) -> None:
        ds = SupabaseDataSource(
            url="https://test.supabase.co", api_key="test-key"
        )
        await ds.connect()
        assert ds._client is not None

        try:
            mock_response = httpx.Response(
                200,
                json=[],
                request=httpx.Request("GET", "https://test.supabase.co/rest/v1/empty"),
            )

            with patch.object(
                ds._client, "get", new_callable=AsyncMock, return_value=mock_response
            ):
                result = await ds.execute("empty")
                assert result.columns == []
                assert result.rows == []
                assert result.row_count == 0
        finally:
            await ds.close()

    async def test_not_connected_raises(self) -> None:
        ds = SupabaseDataSource(
            url="https://test.supabase.co", api_key="test-key"
        )
        with pytest.raises(RuntimeError, match="Not connected"):
            await ds.execute("users")

    async def test_list_tables_returns_empty(self) -> None:
        ds = SupabaseDataSource(
            url="https://test.supabase.co", api_key="test-key"
        )
        await ds.connect()
        try:
            tables = await ds.list_tables()
            assert tables == []
        finally:
            await ds.close()

    async def test_describe_table_minimal(self) -> None:
        ds = SupabaseDataSource(
            url="https://test.supabase.co", api_key="test-key"
        )
        await ds.connect()
        try:
            info = await ds.describe_table("users")
            assert info.name == "users"
            assert info.columns == []
            assert info.row_count is None
        finally:
            await ds.close()

    async def test_context_manager(self) -> None:
        async with SupabaseDataSource(
            url="https://test.supabase.co", api_key="test-key"
        ) as ds:
            assert ds._client is not None
        assert ds._client is None

    async def test_connect_headers(self) -> None:
        ds = SupabaseDataSource(
            url="https://test.supabase.co/", api_key="my-key"
        )
        await ds.connect()
        try:
            assert ds._client is not None
            headers = ds._client.headers
            assert headers["apikey"] == "my-key"
            assert headers["authorization"] == "Bearer my-key"
        finally:
            await ds.close()

# Data Sources

The OpenClaw SDK provides a unified async interface for connecting agents to
databases and REST data backends. Whether you need a zero-dependency SQLite
store for prototyping or a production PostgreSQL pool, every backend implements
the same `DataSource` ABC so your application code stays consistent.

## Quick Start

SQLite requires no extra dependencies -- it uses Python's built-in `sqlite3`
module with async wrappers.

```python
import asyncio
from openclaw_sdk.data import SQLiteDataSource

async def main():
    async with SQLiteDataSource(":memory:") as db:
        await db.execute(
            "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)"
        )
        await db.execute(
            "INSERT INTO users (name, email) VALUES (?, ?)",
            ["Alice", "alice@example.com"],
        )

        # Fetch a single row as a dict
        user = await db.fetch_one("SELECT * FROM users WHERE id = ?", [1])
        print(user)  # {'id': 1, 'name': 'Alice', 'email': 'alice@example.com'}

        # Fetch all rows as a list of dicts
        users = await db.fetch_all("SELECT * FROM users")
        print(f"Total users: {len(users)}")

asyncio.run(main())
```

## DataSource ABC

All data sources implement the `DataSource` abstract base class. This guarantees
a consistent interface across SQLite, PostgreSQL, MySQL, and Supabase backends.

### Abstract Methods

Every backend must implement these five methods:

| Method             | Signature                                            | Description                                   |
|--------------------|------------------------------------------------------|-----------------------------------------------|
| `connect()`        | `async def connect() -> None`                        | Open the connection or connection pool         |
| `close()`          | `async def close() -> None`                          | Close the connection or connection pool        |
| `execute()`        | `async def execute(query, params?) -> QueryResult`   | Execute a query with optional positional params |
| `list_tables()`    | `async def list_tables() -> list[str]`               | Return a sorted list of table names            |
| `describe_table()` | `async def describe_table(table) -> TableInfo`       | Return column metadata for a table             |

### Convenience Methods

These are built on top of `execute()` and are available on every data source:

| Method        | Return Type              | Description                                          |
|---------------|--------------------------|------------------------------------------------------|
| `fetch_one()` | `dict[str, Any] | None`  | Execute a query and return the first row as a dict   |
| `fetch_all()` | `list[dict[str, Any]]`   | Execute a query and return all rows as a list of dicts |

### Async Context Manager

Every data source supports `async with`, which calls `connect()` on entry and
`close()` on exit:

```python
async with SQLiteDataSource("app.db") as db:
    result = await db.execute("SELECT COUNT(*) FROM orders")
    # connection is automatically closed when the block exits
```

## QueryResult

The `QueryResult` Pydantic model is returned by every `execute()` call.

| Field               | Type              | Default | Description                              |
|---------------------|-------------------|---------|------------------------------------------|
| `columns`           | `list[str]`       | `[]`    | Column names from the result set         |
| `rows`              | `list[list[Any]]` | `[]`    | List of rows, each row is a list of values |
| `row_count`         | `int`             | `0`     | Number of rows returned                  |
| `execution_time_ms` | `float`           | `0.0`   | Wall-clock execution time in milliseconds |

```python
result = await db.execute("SELECT id, name FROM users")
print(result.columns)          # ['id', 'name']
print(result.row_count)        # 3
print(result.execution_time_ms) # 0.42
for row in result.rows:
    print(row)                 # [1, 'Alice'], [2, 'Bob'], ...
```

## Schema Introspection

Every data source supports schema introspection through `list_tables()` and
`describe_table()`. The results use the `TableInfo` and `ColumnInfo` models.

### TableInfo

| Field       | Type               | Description                       |
|-------------|--------------------|-----------------------------------|
| `name`      | `str`              | Table name                        |
| `columns`   | `list[ColumnInfo]` | Column metadata                   |
| `row_count` | `int | None`       | Row count (if available)          |

### ColumnInfo

| Field         | Type   | Default | Description                    |
|---------------|--------|---------|--------------------------------|
| `name`        | `str`  | --      | Column name                    |
| `data_type`   | `str`  | --      | Column data type               |
| `nullable`    | `bool` | `True`  | Whether the column is nullable |
| `primary_key` | `bool` | `False` | Whether the column is a PK     |

```python
tables = await db.list_tables()
for table_name in tables:
    info = await db.describe_table(table_name)
    print(f"{info.name} ({info.row_count} rows)")
    for col in info.columns:
        pk = " [PK]" if col.primary_key else ""
        print(f"  {col.name}: {col.data_type}{pk}")
```

## SQLiteDataSource

Zero-dependency SQLite backend using Python's built-in `sqlite3` module. All
blocking I/O is delegated to a thread via `asyncio.to_thread` so the event
loop is never blocked.

| Parameter   | Type   | Default      | Description                                       |
|-------------|--------|--------------|---------------------------------------------------|
| `database`  | `str`  | `":memory:"` | Path to the SQLite file, or `":memory:"`          |
| `read_only` | `bool` | `False`      | Only allow `SELECT` and `PRAGMA` statements       |

```python
from openclaw_sdk.data import SQLiteDataSource

# In-memory database (great for testing)
db = SQLiteDataSource()

# File-backed database
db = SQLiteDataSource("data/app.db")

# Read-only mode (raises PermissionError on INSERT/UPDATE/DELETE)
db = SQLiteDataSource("data/app.db", read_only=True)
```

!!! tip "Read-only mode for safety"
    When connecting agents to a production database, use `read_only=True` to
    prevent the agent from modifying data. In read-only mode, only `SELECT`
    and `PRAGMA` statements are permitted. File-backed databases are opened
    with the SQLite `?mode=ro` URI flag.

## PostgresDataSource

PostgreSQL backend using `asyncpg` with connection pooling.

**Install:** `pip install openclaw-sdk[data-postgres]`

| Parameter       | Type  | Default | Description                            |
|-----------------|-------|---------|----------------------------------------|
| `dsn`           | `str` | --      | PostgreSQL connection string            |
| `min_pool_size` | `int` | `2`     | Minimum connections in the pool         |
| `max_pool_size` | `int` | `10`    | Maximum connections in the pool         |

```python
from openclaw_sdk.data.postgres_source import PostgresDataSource

async with PostgresDataSource(
    dsn="postgresql://user:pass@localhost:5432/mydb",
    min_pool_size=2,
    max_pool_size=20,
) as db:
    result = await db.execute(
        "SELECT id, name FROM users WHERE active = $1", [True]
    )
    print(result.rows)
```

!!! warning "Import guard"
    `PostgresDataSource` is only available when `asyncpg` is installed. If
    you import it without the dependency, you will get an `ImportError` with
    installation instructions. Use the extras install:
    `pip install openclaw-sdk[data-postgres]`.

## MySQLDataSource

MySQL backend using `aiomysql` with connection pooling.

**Install:** `pip install openclaw-sdk[data-mysql]`

| Parameter       | Type  | Default  | Description                      |
|-----------------|-------|----------|----------------------------------|
| `host`          | `str` | --       | Database server hostname         |
| `port`          | `int` | `3306`   | Database server port             |
| `user`          | `str` | `"root"` | Database user                    |
| `password`      | `str` | `""`     | Database password                |
| `database`      | `str` | `""`     | Database name                    |
| `min_pool_size` | `int` | `1`      | Minimum connections in the pool  |
| `max_pool_size` | `int` | `10`     | Maximum connections in the pool  |

```python
from openclaw_sdk.data.mysql_source import MySQLDataSource

async with MySQLDataSource(
    host="localhost",
    user="app",
    password="secret",
    database="mydb",
    max_pool_size=20,
) as db:
    result = await db.execute(
        "SELECT id, name FROM users WHERE active = %s", [1]
    )
    print(result.rows)
```

!!! warning "Import guard"
    `MySQLDataSource` is only available when `aiomysql` is installed. If
    you import it without the dependency, you will get an `ImportError` with
    installation instructions. Use the extras install:
    `pip install openclaw-sdk[data-mysql]`.

## SupabaseDataSource

Supabase REST API backend using `httpx`. Connects to the PostgREST-compatible
endpoint that every Supabase project exposes. No additional dependencies
beyond `httpx` (already a core SDK dependency).

| Parameter | Type    | Default | Description                            |
|-----------|---------|---------|----------------------------------------|
| `url`     | `str`   | --      | Supabase project URL                   |
| `api_key` | `str`   | --      | Supabase `anon` or `service_role` key  |
| `timeout` | `float` | `30.0`  | HTTP request timeout in seconds        |

```python
from openclaw_sdk.data import SupabaseDataSource

async with SupabaseDataSource(
    url="https://xyzcompany.supabase.co",
    api_key="eyJhbGci...",
) as db:
    # Simple table query (SELECT *)
    result = await db.execute("users")
    print(result.rows)

    # Call a Postgres RPC function
    result = await db.execute("rpc:get_active_users")
    print(result.rows)
```

The `query` argument to `execute()` works differently for Supabase:

- A bare table name (e.g. `"users"`) performs a `GET /<table>` request (PostgREST `SELECT *`).
- An `"rpc:<function_name>"` prefix calls a Postgres RPC function via `POST /rpc/<function_name>`.

!!! tip "Schema introspection"
    The Supabase REST API does not expose a table-listing endpoint, so
    `list_tables()` returns an empty list and `describe_table()` returns
    minimal metadata. For full introspection, query `information_schema`
    via an RPC function.

## DataSourceRegistry

The `DataSourceRegistry` provides centralised management of multiple named
data sources. Register them once at startup, look them up by name anywhere
in your application, and close them all together at shutdown.

```python
from openclaw_sdk.data import DataSourceRegistry, SQLiteDataSource

registry = DataSourceRegistry()

# Register data sources
users_db = SQLiteDataSource("data/users.db")
await users_db.connect()
registry.register("users", users_db)

analytics_db = SQLiteDataSource("data/analytics.db")
await analytics_db.connect()
registry.register("analytics", analytics_db)

# Look up by name
db = registry.get("users")
result = await db.fetch_all("SELECT * FROM users LIMIT 10")

# List all registered sources
print(registry.list_sources())  # ['analytics', 'users']

# Close everything at shutdown
await registry.close_all()
```

| Method           | Description                                       |
|------------------|---------------------------------------------------|
| `register(name, source)` | Register a data source under a name. Raises `ValueError` if the name is already taken. |
| `get(name)`      | Return the data source by name. Raises `KeyError` if not found. |
| `list_sources()` | Return a sorted list of registered names.          |
| `close_all()`    | Close every registered data source and clear the registry. |

!!! warning "Duplicate names"
    Calling `register()` with a name that is already registered raises a
    `ValueError`. Unregister or close the existing source first if you need
    to replace it.

## Choosing a Backend

| Backend              | Best For                                | Extra Dependency |
|----------------------|-----------------------------------------|------------------|
| `SQLiteDataSource`   | Prototyping, testing, embedded apps     | None             |
| `PostgresDataSource` | Production workloads, connection pooling | `asyncpg`        |
| `MySQLDataSource`    | MySQL/MariaDB environments              | `aiomysql`       |
| `SupabaseDataSource` | Supabase-hosted projects, REST access   | None (`httpx`)   |

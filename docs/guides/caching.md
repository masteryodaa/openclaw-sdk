# Caching

The OpenClaw SDK includes a built-in response caching layer that can dramatically
reduce latency and cost for repeated queries. Caching is transparent: when enabled,
`agent.execute()` checks the cache before making a gateway call and stores successful
results automatically.

## Quick Start

```python
import asyncio
from openclaw_sdk import OpenClawClient, InMemoryCache

async def main():
    cache = InMemoryCache(ttl_seconds=300, max_size=1000)

    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        client.cache = cache
        agent = client.get_agent("assistant")

        # First call hits the gateway
        result = await agent.execute("What is the capital of France?")
        print(f"Latency: {result.latency_ms}ms")  # e.g. 1200ms

        # Second identical call returns from cache
        result = await agent.execute("What is the capital of France?")
        print(f"Latency: {result.latency_ms}ms")  # 0ms (cache hit)

asyncio.run(main())
```

## How It Works

The cache key is a hash of `(agent_id, query)`. When `agent.execute()` is called:

1. The SDK computes the cache key from the agent ID and the query string.
2. If a cached `ExecutionResult` exists and has not expired, it is returned
   immediately with `latency_ms=0`.
3. If no cache entry exists (or it has expired), the call proceeds to the
   gateway. On success, the result is stored in the cache.

!!! tip "Cache hits are free"
    A cached response returns an `ExecutionResult` with `latency_ms=0` and
    incurs zero token usage. This makes caching especially valuable for
    demo apps, retry loops, and batch jobs with duplicate queries.

## InMemoryCache

`InMemoryCache` is the built-in cache backend. It combines LRU eviction with
time-based expiration.

```python
from openclaw_sdk import InMemoryCache

# Defaults: 5-minute TTL, 1000 entry limit
cache = InMemoryCache()

# Custom settings: 1-hour TTL, 5000 entries
cache = InMemoryCache(ttl_seconds=3600, max_size=5000)
```

| Parameter      | Type  | Default | Description                          |
|----------------|-------|---------|--------------------------------------|
| `ttl_seconds`  | `int` | `300`   | Seconds before a cache entry expires |
| `max_size`     | `int` | `1000`  | Maximum number of cached entries     |

When `max_size` is reached, the least-recently-used entry is evicted to make
room for the new one.

!!! warning "In-memory only"
    `InMemoryCache` lives in process memory. It is lost when your application
    restarts and is not shared across multiple processes. For persistent or
    distributed caching, implement a custom backend.

## Custom Cache Backends

To use Redis, a database, or any other storage, extend the `ResponseCache` ABC:

```python
import asyncio
from openclaw_sdk import ResponseCache, ExecutionResult

class RedisCache(ResponseCache):
    def __init__(self, redis_url: str, ttl_seconds: int = 300):
        self._url = redis_url
        self._ttl = ttl_seconds
        # Initialize your Redis client here

    async def get(self, key: str) -> ExecutionResult | None:
        # Return cached ExecutionResult or None on miss
        ...

    async def set(self, key: str, result: ExecutionResult) -> None:
        # Store the result with TTL
        ...

    async def invalidate(self, key: str) -> None:
        # Remove a specific entry
        ...

    async def clear(self) -> None:
        # Flush all cached entries
        ...
```

Wire it into the client exactly the same way:

```python
async def main():
    cache = RedisCache("redis://localhost:6379", ttl_seconds=600)

    async with OpenClawClient.connect("ws://127.0.0.1:18789/gateway") as client:
        client.cache = cache
        agent = client.get_agent("assistant")
        result = await agent.execute("Summarize today's news")
        print(result.output)

asyncio.run(main())
```

## Invalidating the Cache

You can manually clear entries when you know the underlying data has changed:

```python
# Clear a specific entry
await client.cache.invalidate(key)

# Clear the entire cache
await client.cache.clear()
```

!!! note "Cache scope"
    The cache is scoped to `(agent_id, query)` pairs. Different agents or
    different queries always produce different cache keys, even if the
    underlying LLM would return the same answer.

## When to Use Caching

Caching works best for:

- **Deterministic queries** where the same input reliably produces the same output.
- **High-traffic applications** that repeat common questions (FAQs, lookups).
- **Development and testing** to avoid burning tokens on repeated runs.

Caching is less useful for:

- Queries that depend on real-time data or external tool calls.
- Creative tasks where varied output is desired.
- Long-running conversations with evolving context.

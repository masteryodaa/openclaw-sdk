# Request Deduplication & Semantic Cache

The OpenClaw SDK provides two complementary strategies for avoiding redundant
gateway calls: **request deduplication** (exact match by SHA-256 hash) and
**semantic caching** (fuzzy match by embedding cosine similarity). Use them
independently or together to reduce latency, save tokens, and prevent
duplicate side effects.

## Quick Start

### Request Deduplication

```python
import asyncio
from openclaw_sdk.core.dedup import RequestDeduplicator

async def main():
    dedup = RequestDeduplicator(ttl_seconds=30.0, max_size=5000)

    # First call -- new request
    is_dup = await dedup.check_and_mark("chat.send", {"message": "Hello"})
    print(is_dup)  # False

    # Same call within TTL -- duplicate
    is_dup = await dedup.check_and_mark("chat.send", {"message": "Hello"})
    print(is_dup)  # True

    # Different params -- new request
    is_dup = await dedup.check_and_mark("chat.send", {"message": "Hi"})
    print(is_dup)  # False

    print(f"Tracked entries: {dedup.size}")  # 2

asyncio.run(main())
```

### Semantic Cache

```python
import asyncio
from openclaw_sdk.cache.semantic import SemanticCache
from openclaw_sdk.cache.embeddings import SimpleEmbeddingProvider
from openclaw_sdk.core.types import ExecutionResult

async def main():
    provider = SimpleEmbeddingProvider(dimensions=128)
    cache = SemanticCache(
        embedding_provider=provider,
        similarity_threshold=0.85,
        ttl_seconds=300.0,
    )

    # Store a result
    result = ExecutionResult(output="Paris is the capital of France.")
    await cache.set("assistant", "What is the capital of France?", result)

    # Exact match -- cache hit
    hit = await cache.get("assistant", "What is the capital of France?")
    print(hit.output)  # "Paris is the capital of France."

    # Different agent -- cache miss (agent isolation)
    miss = await cache.get("other-agent", "What is the capital of France?")
    print(miss)  # None

asyncio.run(main())
```

## RequestDeduplicator

The `RequestDeduplicator` prevents duplicate gateway calls within a
configurable time window. It computes a SHA-256 hash of the `(method, params)`
pair and tracks recent requests using an `OrderedDict` for O(1) LRU eviction.

### How It Works

1. When `check_and_mark()` is called, a deterministic SHA-256 key is computed
   from `json.dumps({"method": method, "params": params}, sort_keys=True)`.
2. If the key exists in the store and has not expired (within `ttl_seconds`),
   the request is reported as a **duplicate** and `True` is returned.
3. If the key does not exist or has expired, it is marked as seen with the
   current monotonic timestamp, and `False` is returned.
4. When the store exceeds `max_size`, the oldest (least-recently-seen) entry
   is evicted.

### Parameters

| Parameter     | Type    | Default  | Description                                       |
|---------------|---------|----------|---------------------------------------------------|
| `ttl_seconds` | `float` | `60.0`   | Time-to-live for each dedup entry in seconds       |
| `max_size`    | `int`   | `10000`  | Maximum entries before LRU eviction kicks in       |

### Methods

| Method                          | Return Type | Description                                              |
|---------------------------------|-------------|----------------------------------------------------------|
| `check_and_mark(method, params)` | `bool`     | `True` if duplicate (within TTL), `False` if new         |
| `clear()`                       | `None`      | Remove all tracked entries                               |
| `size`                          | `int`       | Number of currently tracked entries (property)           |

### Thread Safety

The deduplicator uses an `asyncio.Lock` internally, so it is safe to call
from multiple concurrent coroutines.

```python
# Safe to use concurrently
tasks = [
    dedup.check_and_mark("chat.send", {"message": f"msg-{i}"})
    for i in range(100)
]
results = await asyncio.gather(*tasks)
```

!!! tip "Choosing TTL"
    Set `ttl_seconds` based on how long you want to suppress duplicates.
    For chat applications, 30-60 seconds prevents accidental double-sends.
    For batch jobs, a longer TTL (300+ seconds) avoids reprocessing the
    same items within a run.

!!! warning "In-memory only"
    The deduplicator stores entries in process memory. It does not persist
    across restarts and is not shared between processes. For distributed
    deduplication, implement a similar pattern backed by Redis or another
    shared store.

## SemanticCache

The `SemanticCache` is a `ResponseCache` implementation that matches queries
by cosine similarity of their embedding vectors rather than exact string
equality. This means semantically similar queries like "What's France's
capital?" and "Capital of France?" can share cached results.

### How It Works

1. When `get()` is called, the query is embedded using the configured
   `EmbeddingProvider`.
2. Expired entries are pruned (entries older than `ttl_seconds`).
3. Remaining entries are filtered by `agent_id` (different agents never
   share cached results).
4. The entry with the highest cosine similarity above `similarity_threshold`
   is returned.
5. When `set()` is called, the query is embedded and stored alongside
   the `ExecutionResult`. Oldest entries are evicted when `max_size` is exceeded.

### Parameters

| Parameter              | Type                | Default | Description                                    |
|------------------------|---------------------|---------|------------------------------------------------|
| `embedding_provider`   | `EmbeddingProvider` | --      | Provider used to compute embedding vectors     |
| `similarity_threshold` | `float`             | `0.85`  | Minimum cosine similarity for a cache hit      |
| `ttl_seconds`          | `float`             | `300.0` | Time-to-live for each entry in seconds         |
| `max_size`             | `int`               | `1000`  | Maximum number of entries before eviction       |

### Methods

| Method                          | Return Type              | Description                                 |
|---------------------------------|--------------------------|---------------------------------------------|
| `get(agent_id, query)`          | `ExecutionResult | None` | Find a cached result by semantic similarity |
| `set(agent_id, query, result)`  | `None`                   | Store a result in the cache                 |
| `clear()`                       | `None`                   | Remove all entries                          |

### Agent Isolation

The semantic cache enforces strict agent isolation. A query cached for
`agent-a` will never be returned for `agent-b`, even if the queries are
semantically identical. This prevents cross-contamination between agents
that may have different system prompts, tools, or knowledge bases.

```python
# Cached for "assistant"
await cache.set("assistant", "What is 2+2?", result_a)

# Returns result_a
hit = await cache.get("assistant", "What is 2+2?")

# Returns None -- different agent
miss = await cache.get("math-tutor", "What is 2+2?")
```

### Tuning the Similarity Threshold

The `similarity_threshold` controls how similar two queries must be for a
cache hit. Lower values produce more hits but may return less relevant
cached results.

| Threshold | Behavior                                                   |
|-----------|------------------------------------------------------------|
| `0.95`    | Very strict -- only near-identical queries match           |
| `0.85`    | Balanced (default) -- catches common rephrasings           |
| `0.75`    | Loose -- more hits, but may match less relevant queries    |
| `0.50`    | Very loose -- likely too aggressive for most use cases     |

!!! tip "Start with the default"
    The default threshold of `0.85` works well for most applications.
    Monitor your hit rate and adjust up (stricter) if you see irrelevant
    cache hits, or down (looser) if you want more cache reuse.

## EmbeddingProvider ABC

Both the semantic cache and any custom similarity logic can plug in different
embedding backends by implementing the `EmbeddingProvider` abstract base class.

### Abstract Method

| Method              | Signature                                | Description                                |
|---------------------|------------------------------------------|--------------------------------------------|
| `embed(text)`       | `async def embed(text: str) -> list[float]` | Generate an embedding vector for the text |

### Static Utility

| Method                       | Signature                                              | Description                               |
|------------------------------|--------------------------------------------------------|-------------------------------------------|
| `cosine_similarity(a, b)`    | `(a: list[float], b: list[float]) -> float`            | Compute cosine similarity between two vectors. Pure Python, no numpy required. Returns `0.0` if either vector has zero magnitude. |

## SimpleEmbeddingProvider

Hash-based deterministic pseudo-embeddings for testing. Uses SHA-512 to
generate a fixed-size vector from text. The output is deterministic: the
same input always produces the same embedding.

| Parameter    | Type  | Default | Description                         |
|--------------|-------|---------|-------------------------------------|
| `dimensions` | `int` | `128`   | Length of the output embedding vector |

```python
from openclaw_sdk.cache.embeddings import SimpleEmbeddingProvider

provider = SimpleEmbeddingProvider(dimensions=128)
embedding = await provider.embed("Hello world")
print(len(embedding))  # 128
```

!!! warning "Not for production"
    `SimpleEmbeddingProvider` generates pseudo-embeddings from SHA-512 hashes.
    It is deterministic and fast, making it ideal for unit tests, but it does
    **not** capture real semantic similarity. Use `OpenAIEmbeddingProvider`
    or a custom provider for production workloads.

## OpenAIEmbeddingProvider

Production-ready embedding provider that calls the OpenAI `/v1/embeddings`
API via `httpx`.

| Parameter | Type  | Default                       | Description              |
|-----------|-------|-------------------------------|--------------------------|
| `api_key` | `str` | --                            | OpenAI API key           |
| `model`   | `str` | `"text-embedding-3-small"`    | Embedding model name     |

```python
from openclaw_sdk.cache.embeddings import OpenAIEmbeddingProvider

provider = OpenAIEmbeddingProvider(
    api_key="sk-xxx",
    model="text-embedding-3-small",
)
embedding = await provider.embed("What is the capital of France?")
print(len(embedding))  # 1536 (for text-embedding-3-small)
```

!!! tip "Model selection"
    `text-embedding-3-small` is the default and offers a good balance of
    quality and cost. For higher accuracy, use `text-embedding-3-large`.
    For legacy compatibility, `text-embedding-ada-002` is also supported.

## Combining Deduplication and Semantic Cache

For maximum efficiency, use both layers together. The deduplicator catches
exact duplicates instantly (no embedding computation needed), while the
semantic cache catches rephrasings that slip through:

```python
import asyncio
from openclaw_sdk.core.dedup import RequestDeduplicator
from openclaw_sdk.cache.semantic import SemanticCache
from openclaw_sdk.cache.embeddings import OpenAIEmbeddingProvider

async def smart_execute(
    dedup: RequestDeduplicator,
    cache: SemanticCache,
    agent_id: str,
    query: str,
):
    # Layer 1: Exact deduplication (fastest, no network call)
    is_dup = await dedup.check_and_mark("chat.send", {"message": query})
    if is_dup:
        print("Exact duplicate -- skipped")
        return None

    # Layer 2: Semantic cache (embedding lookup)
    cached = await cache.get(agent_id, query)
    if cached is not None:
        print(f"Semantic cache hit")
        return cached

    # Layer 3: Actual gateway call
    result = await execute_on_gateway(agent_id, query)  # your logic here
    await cache.set(agent_id, query, result)
    return result


async def main():
    dedup = RequestDeduplicator(ttl_seconds=60.0)
    provider = OpenAIEmbeddingProvider(api_key="sk-xxx")
    cache = SemanticCache(embedding_provider=provider, similarity_threshold=0.85)

    # First call -- goes to gateway
    await smart_execute(dedup, cache, "assistant", "What is Python?")

    # Exact repeat within TTL -- caught by deduplicator
    await smart_execute(dedup, cache, "assistant", "What is Python?")

    # Rephrased -- caught by semantic cache
    await smart_execute(dedup, cache, "assistant", "Tell me about Python")

asyncio.run(main())
```

## Building a Custom EmbeddingProvider

Implement the `EmbeddingProvider` ABC to use any embedding service:

```python
from openclaw_sdk.cache.embeddings import EmbeddingProvider

class CohereEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str = "embed-english-v3.0"):
        self._api_key = api_key
        self._model = model

    async def embed(self, text: str) -> list[float]:
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.cohere.ai/v1/embed",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "texts": [text],
                    "model": self._model,
                    "input_type": "search_query",
                },
            )
            resp.raise_for_status()
            return resp.json()["embeddings"][0]
```

You can then plug this into the `SemanticCache`:

```python
provider = CohereEmbeddingProvider(api_key="co-xxx")
cache = SemanticCache(embedding_provider=provider, similarity_threshold=0.85)
```

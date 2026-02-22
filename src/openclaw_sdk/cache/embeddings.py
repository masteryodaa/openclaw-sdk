"""Embedding providers for semantic similarity caching.

Provides :class:`EmbeddingProvider` (abstract base), :class:`SimpleEmbeddingProvider`
(hash-based deterministic pseudo-embeddings for testing), and
:class:`OpenAIEmbeddingProvider` (OpenAI embeddings API via httpx).
"""

from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from math import sqrt

import httpx
import structlog

logger = structlog.get_logger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers.

    Subclass this to plug in OpenAI, Cohere, local models, or any other
    embedding backend.
    """

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text.

        Args:
            text: The input text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors.

        Pure-Python implementation with no numpy dependency.

        Args:
            a: First embedding vector.
            b: Second embedding vector.

        Returns:
            Cosine similarity in the range ``[-1.0, 1.0]``.
            Returns ``0.0`` if either vector has zero magnitude.
        """
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = sqrt(sum(x * x for x in a))
        mag_b = sqrt(sum(x * x for x in b))
        if mag_a == 0.0 or mag_b == 0.0:
            return 0.0
        return dot / (mag_a * mag_b)


class SimpleEmbeddingProvider(EmbeddingProvider):
    """Hash-based deterministic pseudo-embeddings for testing.

    Uses SHA-512 to generate a fixed-size vector from text.  The output is
    deterministic: the same input always produces the same embedding.  This
    provider is **not** suitable for production semantic search but is ideal
    for unit tests that need repeatable, fast embeddings without network calls.

    Args:
        dimensions: Length of the output embedding vector (default 128).
    """

    def __init__(self, dimensions: int = 128) -> None:
        self._dimensions = dimensions

    async def embed(self, text: str) -> list[float]:
        """Generate a deterministic pseudo-embedding from *text*.

        Steps:
        1. Normalize text (lowercase, strip whitespace).
        2. Hash with SHA-512 (iterating if needed to fill *dimensions*).
        3. Convert hash bytes to float vector.
        4. Normalize to unit vector.

        Args:
            text: The input text.

        Returns:
            A unit-length float vector of size *dimensions*.
        """
        normalized = text.lower().strip()

        # Generate enough hash bytes to fill the requested dimensions.
        # Each float needs 1 byte from the hash, so we need `dimensions` bytes.
        hash_bytes = b""
        counter = 0
        while len(hash_bytes) < self._dimensions:
            data = f"{normalized}:{counter}".encode()
            hash_bytes += hashlib.sha512(data).digest()
            counter += 1

        # Convert bytes to floats in [0, 1).
        raw = [b / 255.0 for b in hash_bytes[: self._dimensions]]

        # Normalize to unit vector.
        magnitude = sqrt(sum(x * x for x in raw))
        if magnitude == 0.0:
            return raw
        return [x / magnitude for x in raw]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI embeddings API via httpx.

    Makes HTTP requests to the OpenAI ``/v1/embeddings`` endpoint.

    Args:
        api_key: OpenAI API key.
        model: Model name (default ``"text-embedding-3-small"``).
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
    ) -> None:
        self._api_key = api_key
        self._model = model

    async def embed(self, text: str) -> list[float]:
        """Generate an embedding via the OpenAI API.

        Args:
            text: The input text to embed.

        Returns:
            The embedding vector from the API response.

        Raises:
            httpx.HTTPStatusError: If the API returns an error status.
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"input": text, "model": self._model},
            )
            resp.raise_for_status()
            data: list[float] = resp.json()["data"][0]["embedding"]
            return data

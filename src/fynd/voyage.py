"""Gets embeddings from Voyage for retrieval measurements.

The CLI supplies query and Paper text. This client reads cached results or
calls the configured MongoDB Atlas endpoint. Each embedding is cached per text.
Request pacing and reported token totals are tracked per client instance."""

import os
import time
from typing import Any, Final

import httpx

from fynd import cache

# Use the configured Atlas host for every embedding request.
BASE_URL: Final = "https://ai.mongodb.com/v1"
EMBEDDING_URL: Final = f"{BASE_URL}/embeddings"

# Reject keys without the prefix expected by this client before making a request.
ATLAS_KEY_PREFIX: Final = "al-"

# Keep the measured model explicit so cached vectors and reports identify it.
EMBEDDING_MODEL: Final = "voyage-3.5-lite"

# Default to 1024 dimensions; measurement also requests 512 for comparison.
DIMENSIONS: Final = 1024

# These pacing and batch settings come from earlier runs, not live account-limit discovery.
MIN_SECONDS_BETWEEN_REQUESTS: Final = 21.0
SLICE_TOKENS: Final = 3000

# Character-based estimates are approximate; they are not a tokenizer or hard token cap.
CHARACTERS_PER_TOKEN: Final = 4

# Give a rate-limit window time to clear before the single retry.
RETRY_WAIT_SECONDS: Final = 60.0

# Bump when request or stored-response rules change to invalidate incompatible entries.
REQUEST_SHAPE_VERSION: Final = 1


class KeyMissing(Exception):
    """Raised when a live request lacks a key with the configured Atlas prefix."""


class RateLimited(Exception):
    """Raised when Voyage returns HTTP 429 twice."""


class ReplyIncomplete(Exception):
    """Raised when a reply carries no vector for a text that was sent."""


def estimated_tokens(text: str) -> int:
    """Estimates token count using four characters per token plus one."""
    return len(text) // CHARACTERS_PER_TOKEN + 1


def slices(texts: list[str], budget: int = SLICE_TOKENS) -> list[list[str]]:
    """Groups texts by estimated tokens, keeping an oversized text alone."""
    groups: list[list[str]] = []
    running = 0
    # A single oversized text stays intact rather than losing a Paper from the pool.
    for text in texts:
        cost = estimated_tokens(text)
        if groups and running + cost <= budget:
            groups[-1].append(text)
            running += cost
            continue
        groups.append([text])
        running = cost
    return groups


class Voyage:
    """A hosted retrieval-model client with caching, pacing, and reported token usage."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.api_key = os.environ.get("VOYAGE_API_KEY", "")
        # Tests supply local HTTP replies; the default client has a 60-second network timeout.
        self.client = client or httpx.Client(timeout=60.0)
        # Track service-reported tokens, not currency or a spending limit.
        self.tokens_used = 0
        # Pacing is per client; separate instances do not share their timing.
        self.last_request_at: float | None = None

    def embed(
        self, texts: list[str], input_type: str, dimensions: int = DIMENSIONS
    ) -> list[list[float]]:
        """Returns embeddings in input order, requesting only uncached unique texts."""
        # Query and document modes are part of each key because they can produce different vectors.
        keys = [self.embedding_key(text, input_type, dimensions) for text in texts]
        found: dict[str, list[float]] = {}
        for text, key in zip(texts, keys):
            stored = cache.read(key)
            if stored is not None:
                found[text] = stored

        # Send duplicate uncached text only once, then restore duplicates in the returned list.
        missing = []
        for text in texts:
            if text not in found and text not in missing:
                missing.append(text)

        for slice_of_texts in slices(missing):
            payload = self.ask(
                EMBEDDING_URL,
                {
                    "input": slice_of_texts,
                    "model": EMBEDDING_MODEL,
                    "input_type": input_type,
                    "output_dimension": dimensions,
                },
            )
            for item in payload.get("data") or []:
                text = slice_of_texts[item["index"]]
                found[text] = item["embedding"]
                parts = self.embedding_parts(text, input_type, dimensions)
                cache.write(cache.cache_key("voyage-embed", parts), parts, item["embedding"])

        short = [text for text in missing if text not in found]
        if short:
            # Report counts rather than copying Paper abstracts into exception messages.
            raise ReplyIncomplete(
                f"Voyage returned no vector for {len(short)} of {len(missing)} texts. "
                "Nothing was cached for those, so running the command again asks for them."
            )

        return [found[text] for text in texts]

    def embedding_parts(self, text: str, input_type: str, dimensions: int) -> dict[str, Any]:
        """Builds the request details identifying one text embedding."""
        return {
            "api": "voyage-embeddings",
            "model": EMBEDDING_MODEL,
            "input_type": input_type,
            "dimensions": dimensions,
            "text": text,
            "shape": REQUEST_SHAPE_VERSION,
        }

    def embedding_key(self, text: str, input_type: str, dimensions: int) -> str:
        """Builds the cache filename for one embedding request."""
        return cache.cache_key("voyage-embed", self.embedding_parts(text, input_type, dimensions))

    def count_tokens(self, payload: dict[str, Any]) -> None:
        """Adds the response’s reported token usage to this client’s total."""
        usage = payload.get("usage") or {}
        self.tokens_used += usage.get("total_tokens") or 0

    def wait_for_the_rate_limit(self) -> None:
        """Waits for the minimum gap between this client’s request starts."""
        # Wait only the remainder of the 21-second gap; the first request is immediate.
        now = time.monotonic()
        if self.last_request_at is not None:
            due = self.last_request_at + MIN_SECONDS_BETWEEN_REQUESTS
            if due > now:
                time.sleep(due - now)
        self.last_request_at = time.monotonic()

    def ask(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        """Posts a JSON request, retrying HTTP 429 once."""
        if not self.api_key:
            raise KeyMissing(
                "Set VOYAGE_API_KEY in your .env file. The ranking embeds every "
                "abstract in the pool, and Voyage refuses a request with no key. "
                "Make the key in MongoDB Atlas, because this client asks "
                f"{BASE_URL} and an Atlas key is the one that host accepts."
            )
        if not self.api_key.startswith(ATLAS_KEY_PREFIX):
            raise KeyMissing(
                f"This VOYAGE_API_KEY was not made in MongoDB Atlas, and {BASE_URL} "
                f"accepts only a key that begins with {ATLAS_KEY_PREFIX!r}. Make an "
                "Atlas key, or point BASE_URL in src/fynd/voyage.py at "
                "https://api.voyageai.com/v1, which is the host for a key made at "
                "voyageai.com."
            )

        # Retry HTTP 429 once; other HTTP and transport errors propagate.
        for attempt in (1, 2):
            self.wait_for_the_rate_limit()
            response = self.client.post(
                url,
                json=body,
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            if response.status_code != 429:
                response.raise_for_status()
                payload = response.json()
                if url == EMBEDDING_URL:
                    self.count_tokens(payload)
                return payload
            if attempt == 1:
                # Wait 60 seconds before retrying HTTP 429.
                time.sleep(RETRY_WAIT_SECONDS)

        raise RateLimited(
            "Voyage refused the request twice with status 429. Wait a minute and run "
            "the command again. A refused request caches nothing, and every vector an "
            "earlier run did get is still on disk, so the second run pays for the rest."
        )

"""Embed and rerank text with Voyage, and cache every vector on disk.

This is the only paid call in the ranking. The account is prepaid with
automatic recharge off, so the worst case of a loop here is a failed request
and never a bill. See the technical direction table in PRD.md.

The cache holds one vector per text and not one blob per batch. A row of the
measured table embeds a pool that overlaps the pool of the row before it, and a
batch cached whole would pay for all 60 abstracts again to add one Paper.

A vector never enters git. ADR 0011 keeps the text out of the repository, and
a vector of a 2026 model is dead weight once the model changes.
"""

import os
import time
from typing import Any, Final

import httpx

from fynd import cache

# Where the key was made decides the host, and the two do not accept each
# other's keys. A key made in MongoDB Atlas begins with "al-" and answers at
# ai.mongodb.com. A key made at voyageai.com answers at api.voyageai.com. The
# key of this project is an Atlas one. A key scoped to a geography carries it
# in the prefix, as "al-eu-" does, and then the host is eu.ai.mongodb.com.
BASE_URL: Final = "https://ai.mongodb.com/v1"
EMBEDDING_URL: Final = f"{BASE_URL}/embeddings"
RERANK_URL: Final = f"{BASE_URL}/rerank"

# The prefix of an Atlas key. A key with another prefix was made at voyageai.com
# and the host above refuses it with a 401, which is an hour of confusion for a
# reader who did not make the key. So the client says it in a sentence instead.
ATLAS_KEY_PREFIX: Final = "al-"

# One embedding model, which closes the pgvector column size by measurement.
# Two models were the old plan, and on a set of 60 Papers a gap of one or two
# Papers is not a finding, so the comparison could not resolve what it claimed.
EMBEDDING_MODEL: Final = "voyage-4-lite"

# The published size this model serves. The table also reports 512, which a
# caller asks for by passing `dimensions`, so the pgvector column is chosen on
# a measured number and not on a guess.
DIMENSIONS: Final = 1024

# The hosted reranker, and not a local cross encoder. Render's free web service
# holds 512 megabytes, so a local model would measure a path Fynd cannot serve.
RERANK_MODEL: Final = "rerank-3-lite"

# One wait and one retry, which is the rule the Semantic Scholar client already
# follows. Nothing is cached before the answer arrives, so a refusal costs one
# wait and never a wrong vector.
# ponytail: one fixed retry, add real backoff if a run starts failing on this.
RETRY_WAIT_SECONDS: Final = 3.0

# The shape of a stored value, which the cache key carries. A change to what
# this file sends must not serve a vector the old request produced.
REQUEST_SHAPE_VERSION: Final = 1


class KeyMissing(Exception):
    """Raised when there is no Voyage key in the environment."""


class RateLimited(Exception):
    """Raised when Voyage refuses the request twice in a row."""


class ReplyIncomplete(Exception):
    """Raised when a reply does not describe everything the request sent."""


class Voyage:
    """A Voyage client for one run, holding the key and the tokens it spent."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.api_key = os.environ.get("VOYAGE_API_KEY", "")
        # A caller passes a client in a test. A real run makes its own.
        self.client = client or httpx.Client(timeout=60.0)
        # What this run paid for, which the measured table reports. A text the
        # cache already held adds nothing, so this counts the real spend.
        self.tokens_used = 0

    def embed(
        self, texts: list[str], input_type: str, dimensions: int = DIMENSIONS
    ) -> list[list[float]]:
        """Returns one vector for each text, in the order the texts arrived.

        `input_type` is "query" or "document". Voyage embeds the two
        differently, so they are cached apart.
        """
        keys = [self.embedding_key(text, input_type, dimensions) for text in texts]
        found: dict[str, list[float]] = {}
        for text, key in zip(texts, keys):
            stored = cache.read(key)
            if stored is not None:
                found[text] = stored

        # The same text twice in one pool is one request, because a duplicate
        # abstract costs the same tokens as a new one.
        missing = []
        for text in texts:
            if text not in found and text not in missing:
                missing.append(text)

        if missing:
            # ponytail: one request for the whole list. Voyage caps the inputs
            # and the tokens of one call, and 60 abstracts is well inside both.
            # Send the list in slices if a pool ever grows past the cap.
            payload = self.ask(
                EMBEDDING_URL,
                {
                    "input": missing,
                    "model": EMBEDDING_MODEL,
                    "input_type": input_type,
                    "output_dimension": dimensions,
                },
            )
            for item in payload.get("data") or []:
                text = missing[item["index"]]
                found[text] = item["embedding"]
                parts = self.embedding_parts(text, input_type, dimensions)
                cache.write(cache.cache_key("voyage-embed", parts), parts, item["embedding"])

        short = [text for text in missing if text not in found]
        if short:
            # The count and not the text. An abstract in a traceback is an
            # abstract in a log file, and ADR 0011 keeps the text out.
            raise ReplyIncomplete(
                f"Voyage returned no vector for {len(short)} of {len(missing)} texts. "
                "Nothing was cached for those, so running the command again asks for them."
            )

        return [found[text] for text in texts]

    def rerank(self, query: str, documents: list[str]) -> list[tuple[int, float]]:
        """Returns the place of each document and its score, best first.

        The place is a place in the documents list this call was given, because
        the reranker answers in its own order.
        """
        if not documents:
            return []

        parts = {
            "api": "voyage-rerank",
            "model": RERANK_MODEL,
            "query": query,
            "documents": documents,
            "shape": REQUEST_SHAPE_VERSION,
        }
        key = cache.cache_key("voyage-rerank", parts)
        payload = cache.read(key)
        if payload is None:
            payload = self.ask(
                RERANK_URL,
                {"query": query, "documents": documents, "model": RERANK_MODEL},
            )
            if not payload.get("data"):
                # A 200 with an empty body is a failed answer, and the cache
                # module holds that no caller writes one. Cached, it would
                # serve an empty ranking to every later run and a second run
                # could not fix it.
                raise ReplyIncomplete(
                    f"Voyage scored none of the {len(documents)} documents it was sent. "
                    "Nothing was cached, so running the command again asks again."
                )
            cache.write(key, parts, payload)
            # The tokens of a cached answer were paid for by the run that
            # filled the cache, so only a real request adds to the count.
            self.count_tokens(payload)

        places = []
        for item in payload.get("data") or []:
            places.append((item["index"], item["relevance_score"]))
        return places

    def embedding_parts(self, text: str, input_type: str, dimensions: int) -> dict[str, Any]:
        """Returns the values that decide the vector of one text."""
        return {
            "api": "voyage-embeddings",
            "model": EMBEDDING_MODEL,
            "input_type": input_type,
            "dimensions": dimensions,
            "text": text,
            "shape": REQUEST_SHAPE_VERSION,
        }

    def embedding_key(self, text: str, input_type: str, dimensions: int) -> str:
        """Returns the cache file name for the vector of one text."""
        return cache.cache_key("voyage-embed", self.embedding_parts(text, input_type, dimensions))

    def count_tokens(self, payload: dict[str, Any]) -> None:
        """Adds the tokens of one reply to the run total."""
        usage = payload.get("usage") or {}
        self.tokens_used += usage.get("total_tokens") or 0

    def ask(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        """Calls one Voyage endpoint. The only method here that uses the network.

        Raises KeyMissing with no key, and RateLimited after two refusals.
        """
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

        # Two tries at most. Nothing is cached, so a failure costs one wait.
        for attempt in (1, 2):
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
                time.sleep(RETRY_WAIT_SECONDS)

        raise RateLimited(
            "Voyage refused the request twice with status 429. Wait a minute and run "
            "the command again. A refused request caches nothing, and every vector an "
            "earlier run did get is still on disk, so the second run pays for the rest."
        )

"""Search for Papers in the Semantic Scholar Academic Graph API.

Semantic Scholar allows one request per second with a key, so the client waits
between calls, and every reply is cached on disk.
"""

import os
import time
from typing import Any, Final

import httpx

from fynd import cache
from fynd.models import Paper, SearchResult

SEARCH_URL: Final = "https://api.semanticscholar.org/graph/v1/paper/search"

# The fields Fynd needs. Asking for fewer fields keeps the reply small.
FIELDS: Final = "paperId,title,abstract,year,externalIds,openAccessPdf"

# The rate limit the PRD records: one request per second on search with a key.
SECONDS_BETWEEN_REQUESTS: Final = 1.0

# A 429 answer means the rate limit was hit. One retry after a wait is enough,
# because the client already waits a second between its own requests.
# ponytail: one fixed retry, add real backoff if a Stage starts failing on this.
RETRY_WAIT_SECONDS: Final = 3.0

# The shape this file turns a reply into. The cache key carries it, so a change
# to the fields above does not serve an answer parsed by the old rules.
REPLY_SHAPE_VERSION: Final = 2


class RateLimited(Exception):
    """Raised when Semantic Scholar refuses the request twice in a row."""


def paper_from_api(item: dict[str, Any]) -> Paper:
    """Turns one item from the API into a Paper."""
    # The API leaves a field out or sets it to null, so every read has a default.
    external_ids = item.get("externalIds") or {}
    open_access = item.get("openAccessPdf") or {}
    return Paper(
        paper_id=item.get("paperId") or "",
        title=item.get("title") or "",
        abstract=item.get("abstract") or "",
        year=item.get("year"),
        doi=external_ids.get("DOI") or "",
        open_copy_url=open_access.get("url") or "",
    )


class SemanticScholar:
    """A search client for one run, holding the key and the last request time."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
        # A caller passes a client in a test. A real run makes its own.
        self.client = client or httpx.Client(timeout=30.0)
        self.last_request_at = 0.0

    def wait_for_rate_limit(self) -> None:
        """Waits until one second has passed since the last request."""
        if self.last_request_at == 0.0:
            return
        waited = time.monotonic() - self.last_request_at
        remaining = SECONDS_BETWEEN_REQUESTS - waited
        if remaining > 0:
            time.sleep(remaining)

    def search(self, query: str, year_from: int, limit: int = 20) -> SearchResult:
        """Returns the Papers for one query, from the cache when possible.

        `year_from` is the first year the search accepts. The Stage passes it
        in, so this file holds no clock and no window rule of its own.
        """
        year_range = f"{year_from}-"
        parts = {
            "api": "semantic-scholar-search",
            "query": query,
            "limit": limit,
            "year": year_range,
            "fields": FIELDS,
            "shape": REPLY_SHAPE_VERSION,
        }
        key = cache.cache_key("s2-search", parts)
        payload = cache.read(key)
        if payload is None:
            payload = self.fetch_search(query, year_range, limit)
            cache.write(key, parts, payload)

        papers = []
        for item in payload.get("data") or []:
            papers.append(paper_from_api(item))
        return SearchResult(query=query, total=payload.get("total") or 0, papers=papers)

    def fetch_search(self, query: str, year_range: str, limit: int) -> dict[str, Any]:
        """Calls the search endpoint. The only method here that uses the network."""
        headers = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        # Two tries at most. Nothing is cached, so a failure costs one wait.
        for attempt in (1, 2):
            self.wait_for_rate_limit()
            response = self.client.get(
                SEARCH_URL,
                params={
                    "query": query,
                    "limit": limit,
                    "year": year_range,
                    "fields": FIELDS,
                },
                headers=headers,
            )
            self.last_request_at = time.monotonic()

            if response.status_code != 429:
                response.raise_for_status()
                return response.json()

            if attempt == 1:
                time.sleep(RETRY_WAIT_SECONDS)

        raise RateLimited(
            "Semantic Scholar refused the request twice with status 429. "
            "Set SEMANTIC_SCHOLAR_API_KEY in your .env file, because the "
            "endpoint without a key is shared with everyone."
        )

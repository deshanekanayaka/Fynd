"""Finds Papers for Topic checks and retrieval measurements using Semantic Scholar.

Stage 2 and the Retrieval set builder supply search words, a first year, and
a result limit. This client reuses cached replies or requests Paper metadata,
then returns Paper values inside a SearchResult. It does not download files.
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

# Pace this client to the one-request-per-second limit recorded in the PRD.
SECONDS_BETWEEN_REQUESTS: Final = 1.0

# Wait before the single retry; a rate limit is not a result to cache.
RETRY_WAIT_SECONDS: Final = 3.0

# Bump this when response interpretation changes to avoid reusing old entries.
REPLY_SHAPE_VERSION: Final = 2


class RateLimited(Exception):
    """Raised when Semantic Scholar returns HTTP 429 twice."""


def paper_from_api(item: dict[str, Any]) -> Paper:
    """Converts an API record into a Paper, allowing missing metadata."""
    # Missing and null metadata should not prevent us from retaining a Paper.
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
    """A Paper search client with an API key and request timing."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
        # Tests supply a client that returns local replies without network access.
        self.client = client or httpx.Client(timeout=30.0)
        self.last_request_at = 0.0

    def wait_for_rate_limit(self) -> None:
        """Waits for this client's minimum gap after its last response."""
        # Wait only the remaining part of the 1-second gap; the first request is immediate.
        if self.last_request_at == 0.0:
            return
        waited = time.monotonic() - self.last_request_at
        remaining = SECONDS_BETWEEN_REQUESTS - waited
        if remaining > 0:
            time.sleep(remaining)

    def search(self, query: str, year_from: int, limit: int = 20) -> SearchResult:
        """Returns Papers for a query and year range, using cached replies when available."""
        # The caller owns the Evidence window; the trailing dash leaves the end open.
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
        """Requests Paper metadata, retrying HTTP 429 once."""
        headers = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key

        # Keep retries bounded; search writes to the cache only after this succeeds.
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
                # After HTTP 429, wait 3 seconds before the single retry.
                time.sleep(RETRY_WAIT_SECONDS)

        raise RateLimited(
            "Semantic Scholar refused the request twice with status 429. "
            "Set SEMANTIC_SCHOLAR_API_KEY in your .env file, because the "
            "endpoint without a key is shared with everyone."
        )


def cached_abstracts() -> dict[str, str]:
    """Returns locally cached abstracts indexed by Paper identifier."""
    # Grading reads abstracts locally because ADR 0011 keeps them out of git.
    found: dict[str, str] = {}
    for path in sorted(cache.cache_dir().glob("s2-search-*.json")):
        stored = cache.read_file(path)
        if not isinstance(stored, dict) or "value" not in stored:
            continue
        reply = stored["value"]
        if not isinstance(reply, dict):
            continue
        for item in reply.get("data", []):
            abstract = item.get("abstract")
            paper_id = item.get("paperId")
            # Omit missing abstracts so the grading command can report their absence.
            if paper_id and abstract:
                found[paper_id] = abstract
    return found

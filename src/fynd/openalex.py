"""Resolve the Open copy of a Paper a second time, with OpenAlex.

Semantic Scholar hands Fynd one link, and 6 of the 12 links in the first live
run point at doi.org, which redirects to a publisher page Fynd never fetches.
OpenAlex takes the digital object identifier and names every location that
holds the file. See ADR 0007.
"""

from dataclasses import dataclass
from typing import Any, Final
from urllib.parse import quote, urlparse

import httpx

from fynd import cache
from fynd.contact import contact_email, user_agent
from fynd.models import OpenCopy

WORK_URL: Final = "https://api.openalex.org/works/doi:"

# The source type OpenAlex gives a repository. Every other type is a publisher,
# a conference, or a book series, and Fynd fetches none of them.
REPOSITORY_TYPE: Final = "repository"

# The shape this file turns a reply into. The cache key carries it, so a change
# to the rules below does not serve an answer parsed by the old ones.
REPLY_SHAPE_VERSION: Final = 1


class WorkNotRead(Exception):
    """Raised when OpenAlex answers with neither a work nor a plain no."""


@dataclass(frozen=True)
class Resolution:
    """What OpenAlex knows about one digital object identifier.

    Three answers are possible, and the reason table counts them apart. No
    record at all, a record with no repository file, and a record with one.
    """

    found: bool
    open_copy: OpenCopy | None


def host_of(url: str) -> str:
    """Returns the host part of a link, for example `dro.dur.ac.uk`."""
    return urlparse(url).netloc


def is_repository(location: dict[str, Any]) -> bool:
    """Says whether one location sits in a repository and not at a publisher."""
    source = location.get("source") or {}
    return source.get("type") == REPOSITORY_TYPE


def open_copy_from(location: dict[str, Any]) -> OpenCopy | None:
    """Turns one repository location into an Open copy, or returns None."""
    # The PDF link is what the fetcher wants. A repository that gives only a
    # landing page is still worth the attempt, because the fetcher then refuses
    # it and the reason table says "not a PDF", which is a measured fact.
    url = location.get("pdf_url") or location.get("landing_page_url") or ""
    if not url:
        return None
    return OpenCopy(url=url, host=host_of(url), license=location.get("license") or "")


def open_copy_in(work: dict[str, Any]) -> OpenCopy | None:
    """Returns the location Fynd fetches for one work, or None when it has none."""
    best = work.get("best_oa_location") or {}
    if best and is_repository(best):
        return open_copy_from(best)

    for location in work.get("locations") or []:
        if not isinstance(location, dict):
            continue
        if location.get("is_oa") and is_repository(location):
            found = open_copy_from(location)
            if found is not None:
                return found
    return None


class OpenAlex:
    """A lookup client for one run, holding the HTTP client."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        # A caller passes a client in a test. A real run makes its own.
        self.client = client or httpx.Client(timeout=30.0)

    def resolve(self, doi: str) -> Resolution:
        """Returns what OpenAlex knows about one digital object identifier.

        The answer comes from the cache when it is there. All three answers are
        cached, because a Paper OpenAlex does not hold is a fact about the
        Paper and not a failure to retry.
        """
        parts = {
            "api": "openalex-work",
            "doi": doi,
            "shape": REPLY_SHAPE_VERSION,
        }
        key = cache.cache_key("openalex", parts)
        stored = cache.read(key)
        if stored is None:
            stored = self.fetch_work(doi)
            cache.write(key, parts, stored)

        if not stored.get("found"):
            return Resolution(found=False, open_copy=None)
        work = stored.get("work") or {}
        return Resolution(found=True, open_copy=open_copy_in(work))

    def fetch_work(self, doi: str) -> dict[str, Any]:
        """Calls the works endpoint. The only method here that uses the network."""
        # The identifier is escaped, because a real one holds a character that
        # ends a URL path. An unescaped `#` or `?` asks about another work, and
        # that work's file would be measured as this Paper's Source text.
        response = self.client.get(
            WORK_URL + quote(doi, safe=""),
            params={"mailto": contact_email()},
            headers={"User-Agent": user_agent()},
        )
        if response.status_code == 404:
            # OpenAlex holds no record for this identifier. That is an answer.
            return {"found": False, "work": None}
        if response.status_code != 200:
            raise WorkNotRead(
                f"OpenAlex answered {response.status_code} for the identifier {doi}. "
                "Nothing is cached, so the same run tries again when you ask again."
            )
        return {"found": True, "work": response.json()}

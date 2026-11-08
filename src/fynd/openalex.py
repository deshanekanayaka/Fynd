"""Finds candidate Open copy files for a Paper using its DOI.

Stage 2 counts these candidates; the Open copy pipeline tries downloading them.
This client reads cached or live OpenAlex metadata, keeps open PDF locations,
and returns up to three with repositories first. It does not fetch the files.
"""

from dataclasses import dataclass
from typing import Any, Final, Protocol
from urllib.parse import quote, urlparse

import httpx

from fynd import cache, reasons
from fynd.contact import contact_email, user_agent
from fynd.models import OpenCopy

WORK_URL: Final = "https://api.openalex.org/works/doi:"

# Try repositories first; measured publisher refusals motivated this order (ADR 0012).
REPOSITORY_TYPE: Final = "repository"

# These hosts resolve identifiers or index records rather than serve files (ADR 0012).
NO_FILE_HOSTS: Final = ("doi.org", "dx.doi.org", "doaj.org")

# Bound later download attempts to 3 per Paper (ADR 0012).
MAX_CANDIDATES: Final = 3

# Candidate rules run on cached raw metadata, so rule changes need no new lookup.
REPLY_SHAPE_VERSION: Final = 1


class WorkNotRead(Exception):
    """Raised when OpenAlex returns a status other than 200 or 404."""


@dataclass(frozen=True)
class Resolution:
    """A DOI lookup result with ranked file candidates or an absence reason."""

    found: bool
    candidates: tuple[OpenCopy, ...] = ()
    reason: str = ""


def host_of(url: str) -> str:
    """Returns the host part of a link, for example `dro.dur.ac.uk`."""
    return urlparse(url).netloc


def is_repository(location: dict[str, Any]) -> bool:
    """Checks whether OpenAlex labels a location as a repository."""
    source = location.get("source") or {}
    return source.get("type") == REPOSITORY_TYPE


def holds_no_file(url: str) -> bool:
    """Checks whether a URL belongs to a configured non-file host."""
    # Treat DOI.org and www.doi.org as the same blocklisted host.
    host = host_of(url).lower()
    bare = host[4:] if host.startswith("www.") else host
    return bare in NO_FILE_HOSTS


def open_locations(work: dict[str, Any]) -> list[dict[str, Any]]:
    """Collects distinct locations marked open, considering the preferred one first."""
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    best = work.get("best_oa_location") or {}
    for number, location in enumerate([best, *(work.get("locations") or [])]):
        if not isinstance(location, dict) or not location.get("is_oa"):
            continue
        # Retain linkless locations so their reason is no PDF link, not no open location.
        mark = str(location.get("pdf_url") or location.get("landing_page_url") or f"#{number}")
        if mark in seen:
            # The preferred location can also appear in the full locations list.
            continue
        seen.add(mark)
        found.append(location)
    return found


def open_candidates(work: dict[str, Any]) -> list[OpenCopy]:
    """Returns up to three open PDF candidates, with repositories first."""
    # Share these rules between Stage 2's count and the download pipeline.
    repositories: list[OpenCopy] = []
    others: list[OpenCopy] = []
    for location in open_locations(work):
        url = str(location.get("pdf_url") or "")
        if not url or holds_no_file(url):
            continue
        # OpenAlex's open mark qualifies the location even if its licence is missing.
        copy = OpenCopy(url=url, host=host_of(url), license=location.get("license") or "")
        if is_repository(location):
            repositories.append(copy)
        else:
            others.append(copy)
    return [*repositories, *others][:MAX_CANDIDATES]


def reason_for_no_candidate(work: dict[str, Any]) -> str:
    """Explains an empty candidate list using the shared reason names."""
    locations = open_locations(work)
    if not locations:
        return reasons.NO_OPEN_LOCATION
    if not any(location.get("pdf_url") for location in locations):
        return reasons.NO_PDF_LINK
    return reasons.BLOCKLISTED_ONLY


class Resolve(Protocol):
    """A supplied DOI lookup function returning a Resolution."""

    def __call__(self, doi: str) -> Resolution: ...


class OpenAlex:
    """An OpenAlex DOI lookup client."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        # Tests supply local replies; live requests use a 30-second HTTP timeout.
        self.client = client or httpx.Client(timeout=30.0)

    def resolve(self, doi: str) -> Resolution:
        """Returns file candidates or an absence reason, using cached metadata when available."""
        parts = {
            "api": "openalex-work",
            "doi": doi,
            "shape": REPLY_SHAPE_VERSION,
        }
        key = cache.cache_key("openalex", parts)
        stored = cache.read(key)
        if stored is None:
            stored = self.fetch_work(doi)
            # Cache records and confirmed 404s; temporary failures must remain retryable.
            cache.write(key, parts, stored)

        if not stored.get("found"):
            return Resolution(found=False, reason=reasons.NO_OPENALEX_RECORD)
        work = stored.get("work") or {}
        candidates = open_candidates(work)
        if not candidates:
            return Resolution(found=True, reason=reason_for_no_candidate(work))
        return Resolution(found=True, candidates=tuple(candidates))

    def fetch_work(self, doi: str) -> dict[str, Any]:
        """Requests a DOI record, distinguishing not found from a failed lookup."""
        # Escape # and ? so DOI characters cannot change the URL's meaning.
        response = self.client.get(
            WORK_URL + quote(doi, safe=""),
            params={"mailto": contact_email()},
            headers={"User-Agent": user_agent()},
        )
        if response.status_code == 404:
            # A confirmed missing record is a usable answer, unlike a failed request.
            return {"found": False, "work": None}
        if response.status_code != 200:
            raise WorkNotRead(
                f"OpenAlex answered {response.status_code} for the identifier {doi}. "
                "Nothing is cached, so the same run tries again when you ask again."
            )
        return {"found": True, "work": response.json()}

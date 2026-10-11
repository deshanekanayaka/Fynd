"""Resolve the Open copy of a Paper a second time, with OpenAlex.

Semantic Scholar hands Fynd one link, and 6 of the 12 links in the first live
run point at doi.org, which holds no file. OpenAlex takes the digital object
identifier and names every location that holds one.

An open file is a licence question. Every open location with a PDF link is a
candidate, a repository ranks first and a journal second, and the only host
rule left is a blocklist of hosts that hold no file. See ADR 0012, which
supersedes the repository rule of ADR 0007.
"""

from dataclasses import dataclass
from typing import Any, Final
from urllib.parse import quote, urlparse

import httpx

from fynd import cache, reasons
from fynd.contact import contact_email, user_agent
from fynd.models import OpenCopy

WORK_URL: Final = "https://api.openalex.org/works/doi:"

# The source type OpenAlex gives a repository. A repository ranks first,
# because it serves a program and a journal often does not. Every other type
# ranks second, and no type is refused. See ADR 0012.
REPOSITORY_TYPE: Final = "repository"

# The hosts that hold no file by design. This is the only host rule left.
# doi.org and dx.doi.org redirect to a publisher page, and doaj.org is an
# index of journals that answered 2 fetches with a 403 on 2026-10-09.
NO_FILE_HOSTS: Final = ("doi.org", "dx.doi.org", "doaj.org")

# At most this many candidates are offered for one Paper. 19 of the 20 Papers
# of the measured pool hold 3 or fewer, so the cap binds once, and the
# attempts column of the next measurement says whether a fourth would pay.
MAX_CANDIDATES: Final = 3

# The shape of the stored value, which is the raw reply plus a found flag. The
# cache key carries it. The rules above read that raw reply at every call, so
# ADR 0012 changed what a candidate is and left this number alone: the 20
# records in git replay under the new rules with no lookup.
REPLY_SHAPE_VERSION: Final = 1


class WorkNotRead(Exception):
    """Raised when OpenAlex answers with neither a work nor a plain no."""


@dataclass(frozen=True)
class Resolution:
    """What OpenAlex knows about one digital object identifier.

    `candidates` holds the open files Fynd may fetch, already ranked and
    already capped. `reason` says why the list is empty, and it is an empty
    string when the list is not.
    """

    found: bool
    candidates: tuple[OpenCopy, ...] = ()
    reason: str = ""


def host_of(url: str) -> str:
    """Returns the host part of a link, for example `dro.dur.ac.uk`."""
    return urlparse(url).netloc


def is_repository(location: dict[str, Any]) -> bool:
    """Says whether one location sits in a repository and not at a journal."""
    source = location.get("source") or {}
    return source.get("type") == REPOSITORY_TYPE


def holds_no_file(url: str) -> bool:
    """Says whether this host holds no file by design.

    The host is lowercased, and a leading `www.` is dropped, because
    `https://www.doaj.org/article/x` is the same index as `https://doaj.org`.
    """
    host = host_of(url).lower()
    bare = host[4:] if host.startswith("www.") else host
    return bare in NO_FILE_HOSTS


def open_locations(work: dict[str, Any]) -> list[dict[str, Any]]:
    """Returns every open location of one work, best first and once each.

    `best_oa_location` repeats one entry of `locations`, and two attempts at
    one link would spend the cap on it.
    """
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    best = work.get("best_oa_location") or {}
    for number, location in enumerate([best, *(work.get("locations") or [])]):
        if not isinstance(location, dict) or not location.get("is_oa"):
            continue
        # A location with no PDF link is still counted here, because the reason
        # below tells a closed Paper apart from one with a landing page only.
        # A location with no link at all keeps its place in the count under its
        # position, because OpenAlex still calls that location open.
        mark = str(location.get("pdf_url") or location.get("landing_page_url") or f"#{number}")
        if mark in seen:
            continue
        seen.add(mark)
        found.append(location)
    return found


def open_candidates(work: dict[str, Any]) -> list[OpenCopy]:
    """Returns the open files Fynd may fetch for one work, in the order to try.

    A candidate is an open location with a PDF link on a host that holds a
    file. A repository ranks first and a journal second, and inside one rank
    the OpenAlex order stays. The stage 2 gate counts this list, and the
    pipeline fetches it, so neither can count what the other would not try.
    """
    repositories: list[OpenCopy] = []
    others: list[OpenCopy] = []
    for location in open_locations(work):
        url = str(location.get("pdf_url") or "")
        if not url or holds_no_file(url):
            continue
        copy = OpenCopy(url=url, host=host_of(url), license=location.get("license") or "")
        if is_repository(location):
            repositories.append(copy)
        else:
            others.append(copy)
    return [*repositories, *others][:MAX_CANDIDATES]


def reason_for_no_candidate(work: dict[str, Any]) -> str:
    """Returns the reason one work offers no candidate, checked in three steps."""
    locations = open_locations(work)
    if not locations:
        return reasons.NO_OPEN_LOCATION
    if not any(location.get("pdf_url") for location in locations):
        return reasons.NO_PDF_LINK
    return reasons.BLOCKLISTED_ONLY


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
            return Resolution(found=False, reason=reasons.NO_OPENALEX_RECORD)
        work = stored.get("work") or {}
        candidates = open_candidates(work)
        if not candidates:
            return Resolution(found=True, reason=reason_for_no_candidate(work))
        return Resolution(found=True, candidates=tuple(candidates))

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

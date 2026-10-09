"""Join the four steps that turn one Paper into Usable text.

One Paper in, one result out. The result holds the location Fynd took, the
Source text when there is one, and a reason from the eight fixed strings in
`reasons.py`.

This is the file stage 4 calls, so it takes its four jobs as plain function
arguments with no default values, as a Stage file does under ADR 0006. The edge
wires the real ones, and a test passes fakes and performs no HTTP.
"""

from dataclasses import dataclass
from typing import Final, Protocol

from fynd import reasons
from fynd.extract import Extracted
from fynd.fetcher import FetchAnswer, Fetched
from fynd.models import OpenCopy, Paper
from fynd.openalex import Resolution, host_of

# A doi.org link is a lookup key and never a fetch target. ADR 0007 says Fynd
# never fetches a publisher, and this host redirects to one.
LOOKUP_ONLY_HOSTS: Final = ("doi.org", "dx.doi.org")


class Resolve(Protocol):
    """The OpenAlex lookup, which the edge supplies."""

    def __call__(self, doi: str) -> Resolution: ...


class Fetch(Protocol):
    """The fetch of one link, which the edge supplies."""

    def __call__(self, url: str) -> FetchAnswer: ...


class Extract(Protocol):
    """The extraction of one file, which the edge supplies."""

    def __call__(self, data: bytes) -> Extracted: ...


class Check(Protocol):
    """The usable text check, which answers with a reason or an empty string."""

    def __call__(self, text: str) -> str: ...


@dataclass(frozen=True)
class OpenCopyResult:
    """What one Paper gave, and the reason it gave no more than that."""

    paper: Paper
    reason: str
    open_copy: OpenCopy | None = None
    extracted: Extracted | None = None

    @property
    def is_usable(self) -> bool:
        """Says whether this Paper reached Usable text."""
        return self.reason == reasons.USABLE


def fallback_open_copy(paper: Paper) -> OpenCopy | None:
    """Returns the Semantic Scholar link as an Open copy, when Fynd may fetch it."""
    url = paper.open_copy_url
    if not url:
        return None
    host = host_of(url)
    if host in LOOKUP_ONLY_HOSTS:
        # An address with no file behind it. 6 of the 12 links in the first
        # live run were one of these.
        return None
    # The license is unknown here, because only OpenAlex states one.
    return OpenCopy(url=url, host=host, license="")


def locate(paper: Paper, resolve: Resolve) -> tuple[OpenCopy | None, str]:
    """Returns the Open copy to fetch, and the reason when there is none."""
    if not paper.doi:
        found = fallback_open_copy(paper)
        return (found, "") if found else (None, reasons.NO_DOI)

    answer = resolve(paper.doi)
    if answer.open_copy is not None:
        return answer.open_copy, ""

    # OpenAlex gave no file. The Semantic Scholar link is the second chance,
    # and the reason names which of the two misses when it gives none either.
    found = fallback_open_copy(paper)
    if found is not None:
        return found, ""
    if not answer.found:
        return None, reasons.NO_OPENALEX_RECORD
    return None, reasons.NO_REPOSITORY_LOCATION


def read_open_copy(
    paper: Paper,
    resolve: Resolve,
    fetch: Fetch,
    extract: Extract,
    check: Check,
) -> OpenCopyResult:
    """Returns the Usable text of one Paper, or the reason it has none."""
    open_copy, reason = locate(paper, resolve)
    if open_copy is None:
        return OpenCopyResult(paper=paper, reason=reason)

    answer = fetch(open_copy.url)
    if not isinstance(answer, Fetched):
        return OpenCopyResult(paper=paper, reason=answer.reason, open_copy=open_copy)

    extracted = extract(answer.data)
    against = check(extracted.text)
    return OpenCopyResult(
        paper=paper,
        reason=against or reasons.USABLE,
        open_copy=open_copy,
        extracted=extracted,
    )

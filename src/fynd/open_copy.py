"""Join the four steps that turn one Paper into Usable text.

One Paper in, one result out. The result holds the location Fynd took, the
Source text when there is one, the number of links it cost, and a reason from
the fixed strings in `reasons.py`.

This is the file stage 4 calls, so it takes its four jobs as plain function
arguments with no default values, as a Stage file does under ADR 0006. The edge
wires the real ones, and a test passes fakes and performs no HTTP.
"""

from dataclasses import dataclass
from typing import Protocol

from fynd import reasons
from fynd.extract import Extracted
from fynd.fetcher import FetchAnswer, Fetched
from fynd.models import OpenCopy, Paper
from fynd.openalex import Resolution, holds_no_file, host_of


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
    """What one Paper gave, and the reason it gave no more than that.

    `attempts` counts the links fetched for this Paper, and `reason` is the
    reason of the last attempt. One count and one reason, because the only
    reader is a table that counts reasons. See ADR 0012.
    """

    paper: Paper
    reason: str
    open_copy: OpenCopy | None = None
    extracted: Extracted | None = None
    attempts: int = 0

    @property
    def is_usable(self) -> bool:
        """Says whether this Paper reached Usable text."""
        return self.reason == reasons.USABLE


def fallback_open_copy(paper: Paper) -> OpenCopy | None:
    """Returns the Semantic Scholar link as an Open copy, when it holds a file.

    The blocklist applies here as it applies to a candidate. 6 of the 12 links
    of the day 1 pool were doi.org addresses, which hold no file.
    """
    url = paper.open_copy_url
    if not url or holds_no_file(url):
        return None
    # The license is unknown here, because only OpenAlex states one.
    return OpenCopy(url=url, host=host_of(url), license="")


def candidates_for(paper: Paper, resolve: Resolve) -> tuple[list[OpenCopy], str]:
    """Returns the links to try for one Paper, and the reason when there are none.

    OpenAlex ranks and caps the list. The Semantic Scholar link is the last
    resort, and it runs only when OpenAlex names no candidate at all, because
    it produced none of the 5 usable files of 2026-10-09.
    """
    if not paper.doi:
        found = fallback_open_copy(paper)
        return ([found], "") if found else ([], reasons.NO_DOI)

    answer = resolve(paper.doi)
    if answer.candidates:
        return list(answer.candidates), ""

    found = fallback_open_copy(paper)
    if found is not None:
        return [found], ""
    return [], answer.reason


def read_open_copy(
    paper: Paper,
    resolve: Resolve,
    fetch: Fetch,
    extract: Extract,
    check: Check,
) -> OpenCopyResult:
    """Returns the Usable text of one Paper, or the reason it has none.

    Each candidate is fetched in turn, and the first file ends the attempts,
    whether or not its text passes the checks. A second candidate of one Paper
    is the same article, so a failed check is the Paper's answer.
    """
    candidates, reason = candidates_for(paper, resolve)
    if not candidates:
        return OpenCopyResult(paper=paper, reason=reason)

    attempts = 0
    last: OpenCopy | None = None
    last_reason = ""
    for open_copy in candidates:
        attempts += 1
        last = open_copy
        answer = fetch(open_copy.url)
        if isinstance(answer, Fetched):
            extracted = extract(answer.data)
            against = check(extracted.text)
            return OpenCopyResult(
                paper=paper,
                reason=against or reasons.USABLE,
                open_copy=open_copy,
                extracted=extracted,
                attempts=attempts,
            )
        last_reason = answer.reason

    # Every candidate refused. The reason of the last one is the Paper's
    # reason, and the attempts say how many links it cost.
    return OpenCopyResult(
        paper=paper, reason=last_reason, open_copy=last, attempts=attempts
    )

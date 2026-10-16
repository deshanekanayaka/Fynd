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
from fynd.fetcher import FetchAnswer, Fetched, FetchFailed
from fynd.models import OpenCopy, Paper
from fynd.openalex import Resolve, holds_no_file, host_of


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

    `tried_hosts` names every host this Paper cost a fetch, in order, because
    the host table counts links tried and a Paper now tries up to 3. `reason`
    is the reason of the last attempt. See ADR 0012.
    """

    paper: Paper
    reason: str
    open_copy: OpenCopy | None = None
    extracted: Extracted | None = None
    tried_hosts: tuple[str, ...] = ()

    @property
    def is_usable(self) -> bool:
        """Says whether this Paper reached Usable text."""
        return self.reason == reasons.USABLE

    @property
    def attempts(self) -> int:
        """Counts the links this Paper cost."""
        return len(self.tried_hosts)


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
    # A resolver that names no reason would leave a Paper out of the reason
    # table, and that table must sum to the pool.
    return [], answer.reason or reasons.NO_OPEN_LOCATION


def read_open_copy(
    paper: Paper,
    resolve: Resolve,
    fetch: Fetch,
    extract: Extract,
    check: Check,
) -> OpenCopyResult:
    """Returns the Usable text of one Paper, or the reason it has none.

    Each candidate is fetched in turn, and Usable text ends the attempts. A
    file whose text fails a check does not, because the candidates are three
    files of one article and the checks test the file. A scan of paper pages
    extracts to nonsense, and the next candidate can be a clean file.

    A host that refuses never stops the run, and neither does one that times
    out. A timeout is a failure and not an answer, so when no candidate gave a
    file the failure is raised and the caller counts the Paper as dropped.
    """
    candidates, reason = candidates_for(paper, resolve)
    if not candidates:
        return OpenCopyResult(paper=paper, reason=reason)

    tried: list[str] = []
    last: OpenCopy | None = None
    last_reason = ""
    failure: FetchFailed | None = None
    # The last file that arrived and failed a check. It beats a later refusal
    # as the Paper's answer, because the pipeline got one step further with it.
    failed_file: OpenCopyResult | None = None
    for open_copy in candidates:
        tried.append(open_copy.host)
        last = open_copy
        try:
            answer = fetch(open_copy.url)
        except FetchFailed as error:
            # The next candidate is another host, and it may hold the file.
            failure = error
            continue
        if isinstance(answer, Fetched):
            extracted = extract(answer.data)
            against = check(extracted.text)
            result = OpenCopyResult(
                paper=paper,
                reason=against or reasons.USABLE,
                open_copy=open_copy,
                extracted=extracted,
                tried_hosts=tuple(tried),
            )
            if result.is_usable:
                return result
            failed_file = result
            continue
        last_reason = answer.reason

    if failed_file is not None:
        # The hosts of every attempt, including the ones after this file.
        return OpenCopyResult(
            paper=failed_file.paper,
            reason=failed_file.reason,
            open_copy=failed_file.open_copy,
            extracted=failed_file.extracted,
            tried_hosts=tuple(tried),
        )

    if not last_reason and failure is not None:
        # Every candidate failed, and a failure is not an answer. Nothing of it
        # is cached, so the same links are tried again when you ask again.
        raise failure

    # Every candidate refused. The reason of the last one is the Paper's
    # reason, and the hosts say how many links it cost.
    return OpenCopyResult(
        paper=paper, reason=last_reason, open_copy=last, tried_hosts=tuple(tried)
    )

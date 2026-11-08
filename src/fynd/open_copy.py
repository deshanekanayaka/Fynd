"""Connects lookup, downloading, extraction, and text checks for one Paper.

The CLI supplies the four functions; tests supply fakes without network calls.
Candidates are tried in order until one gives Usable text. The result records
the retained location, extracted text, attempted hosts, and a shared reason.
This pipeline is intended for the future Stage 4; it saves no Project state.
"""

from dataclasses import dataclass
from typing import Protocol

from fynd import reasons
from fynd.extract import Extracted
from fynd.fetcher import FetchAnswer, Fetched, FetchFailed
from fynd.models import OpenCopy, Paper
from fynd.openalex import Resolve, holds_no_file, host_of


class Fetch(Protocol):
    """A supplied function that downloads a URL or returns a refusal."""

    def __call__(self, url: str) -> FetchAnswer: ...


class Extract(Protocol):
    """A supplied function that extracts Source text from file bytes."""

    def __call__(self, data: bytes) -> Extracted: ...


class Check(Protocol):
    """A supplied text check returning a failure reason or an empty string."""

    def __call__(self, text: str) -> str: ...


@dataclass(frozen=True)
class OpenCopyResult:
    """One Paper's retained outcome, extracted text, and attempted hosts."""

    paper: Paper
    reason: str
    open_copy: OpenCopy | None = None
    extracted: Extracted | None = None
    tried_hosts: tuple[str, ...] = ()

    @property
    def is_usable(self) -> bool:
        """Checks whether the outcome reason is usable."""
        return self.reason == reasons.USABLE

    @property
    def attempts(self) -> int:
        """Counts candidate links attempted, including cached or refused requests."""
        return len(self.tried_hosts)


def fallback_open_copy(paper: Paper) -> OpenCopy | None:
    """Wraps an unblocked Semantic Scholar link as a fallback candidate."""
    url = paper.open_copy_url
    if not url or holds_no_file(url):
        return None
    # The reported link supplies no licence here and has not yet been fetched.
    return OpenCopy(url=url, host=host_of(url), license="")


def candidates_for(paper: Paper, resolve: Resolve) -> tuple[list[OpenCopy], str]:
    """Chooses OpenAlex candidates or a fallback, with a reason if neither exists."""
    if not paper.doi:
        found = fallback_open_copy(paper)
        return ([found], "") if found else ([], reasons.NO_DOI)

    answer = resolve(paper.doi)
    if answer.candidates:
        # OpenAlex already caps this list at 3; do not add an extra fallback attempt.
        return list(answer.candidates), ""

    found = fallback_open_copy(paper)
    if found is not None:
        return [found], ""
    # Every empty result needs a reason so measurement counts include the Paper.
    return [], answer.reason or reasons.NO_OPEN_LOCATION


def read_open_copy(
    paper: Paper,
    resolve: Resolve,
    fetch: Fetch,
    extract: Extract,
    check: Check,
) -> OpenCopyResult:
    """Tries file candidates until text passes, retaining an outcome when none pass."""
    candidates, reason = candidates_for(paper, resolve)
    if not candidates:
        return OpenCopyResult(paper=paper, reason=reason)

    tried: list[str] = []
    last: OpenCopy | None = None
    last_reason = ""
    failure: FetchFailed | None = None
    # Prefer a file's failed text check over refusals because extraction got further.
    failed_file: OpenCopyResult | None = None
    for open_copy in candidates:
        tried.append(open_copy.host)
        last = open_copy
        try:
            answer = fetch(open_copy.url)
        except FetchFailed as error:
            # A temporary download failure must not discard the remaining candidates.
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
            # Another copy may produce better text; keep this outcome if none does.
            failed_file = result
            continue
        last_reason = answer.reason

    if failed_file is not None:
        # Include attempts made after the retained file, not only its earlier hosts.
        return OpenCopyResult(
            paper=failed_file.paper,
            reason=failed_file.reason,
            open_copy=failed_file.open_copy,
            extracted=failed_file.extracted,
            tried_hosts=tuple(tried),
        )

    if not last_reason and failure is not None:
        # With no file or recorded refusal, preserve the temporary failure for the caller.
        raise failure

    # Retain a refusal rather than turning a temporary failure into a reason.
    return OpenCopyResult(paper=paper, reason=last_reason, open_copy=last, tried_hosts=tuple(tried))

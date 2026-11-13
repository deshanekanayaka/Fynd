"""The pipeline has to reach every reason, and reach them with no HTTP."""

import pytest

from fynd import reasons
from fynd.extract import Extracted
from fynd.fetcher import Fetched, FetchFailed, Refused
from fynd.models import OpenCopy, Paper
from fynd.open_copy import read_open_copy
from fynd.openalex import Resolution
from fynd.source_text import reason_against_paper_text

A_LONG_TEXT = "Results. The household energy demand of England rose again. " * 200
A_SHORT_TEXT = "Please accept our cookies to continue."
REPOSITORY_COPY = OpenCopy(
    url="https://dro.dur.ac.uk/aaa.pdf", host="dro.dur.ac.uk", license="cc-by"
)
JOURNAL_COPY = OpenCopy(url="https://www.mdpi.com/aaa.pdf", host="www.mdpi.com", license="cc-by")

FOUND_ONE = Resolution(found=True, candidates=(REPOSITORY_COPY,))
FOUND_BOTH = Resolution(found=True, candidates=(REPOSITORY_COPY, JOURNAL_COPY))


def paper(**fields) -> Paper:
    """Builds a Paper with the fields a test cares about."""
    values = {"paper_id": "aaa", "title": "A paper", "doi": "10.1000/aaa"}
    values.update(fields)
    return Paper(**values)


def pdf_bytes() -> Fetched:
    return Fetched(data=b"%PDF-1.7", content_type="application/pdf")


def extracted(text: str) -> Extracted:
    return Extracted(text=text, extractor="pdfplumber 0.11.10", structure=[])


def refused(reason: str, status: int = 403) -> Refused:
    return Refused(status=status, content_type="text/html", reason=reason)


def read(
    fields: dict | None = None,
    resolution: Resolution = FOUND_ONE,
    fetch=None,
    text: str = A_LONG_TEXT,
    extract=None,
):
    """Runs the pipeline with fake steps, and changes only what a test names.

    Every test needs all five steps, so the defaults are the happy path: one
    candidate from OpenAlex, a PDF that downloads, and text long enough to
    pass. A test then replaces the one step it is about.
    """
    return read_open_copy(
        paper(**(fields or {})),
        lambda doi: resolution,
        fetch or (lambda url: pdf_bytes()),
        extract or (lambda data: extracted(text)),
        reason_against_paper_text,
    )


def test_a_paper_that_reaches_usable_text() -> None:
    result = read()

    assert result.reason == reasons.USABLE
    assert result.is_usable is True
    assert result.attempts == 1
    assert result.open_copy == REPOSITORY_COPY
    assert result.extracted is not None
    assert result.extracted.text == A_LONG_TEXT


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        # No identifier, so there is nothing to look up.
        ({"fields": {"doi": ""}, "resolution": Resolution(found=False)}, reasons.NO_DOI),
        (
            {"resolution": Resolution(found=False, reason=reasons.NO_OPENALEX_RECORD)},
            reasons.NO_OPENALEX_RECORD,
        ),
        # OpenAlex knows the article and names only the publisher page.
        (
            {"resolution": Resolution(found=True, reason=reasons.NO_OPEN_LOCATION)},
            reasons.NO_OPEN_LOCATION,
        ),
        # A DOI resolver link is a lookup key and never a file target (ADR 0012).
        (
            {
                "fields": {"open_copy_url": "https://doi.org/10.1000/aaa"},
                "resolution": Resolution(found=True, reason=reasons.NO_OPEN_LOCATION),
            },
            reasons.NO_OPEN_LOCATION,
        ),
        ({"resolution": Resolution(found=True, reason=reasons.NO_PDF_LINK)}, reasons.NO_PDF_LINK),
        (
            {"fetch": lambda url: refused(reasons.NOT_A_PDF, status=200)},
            reasons.NOT_A_PDF,
        ),
        ({"text": A_SHORT_TEXT}, reasons.TEXT_TOO_SHORT),
        # Two control characters and two private use glyphs, which is what a
        # badly extracted PDF returns.
        (
            {"text": (chr(1) + chr(2) + chr(0xE000) + chr(0xE001)) * 2000},
            reasons.TEXT_NOT_TEXTUAL,
        ),
    ],
)
def test_the_pipeline_names_the_step_a_paper_reached(case: dict, expected: str) -> None:
    assert read(**case).reason == expected


def test_a_refused_fetch_keeps_the_candidate_and_no_text() -> None:
    result = read(fetch=lambda url: refused(reasons.FETCH_REFUSED))

    assert result.reason == reasons.FETCH_REFUSED
    assert result.open_copy == REPOSITORY_COPY
    assert result.extracted is None


def test_the_semantic_scholar_link_is_the_last_resort() -> None:
    result = read(
        fields={"open_copy_url": "https://www.mdpi.com/aaa.pdf"},
        resolution=Resolution(found=True, reason=reasons.NO_OPEN_LOCATION),
    )

    assert result.reason == reasons.USABLE
    assert result.open_copy is not None
    assert result.open_copy.host == "www.mdpi.com"
    # The fallback link carries no license, because Semantic Scholar names none.
    assert result.open_copy.license == ""


def test_the_semantic_scholar_link_is_not_used_when_openalex_names_one() -> None:
    # The fallback produced none of the 5 usable files of 2026-10-09 and cost
    # 3 refused fetches, so it runs only when OpenAlex names no candidate.
    asked: list = []

    read(fields={"open_copy_url": "https://doaj.org/article/aaa"}, fetch=asks(asked))

    assert asked == [REPOSITORY_COPY.url]


def test_a_fallback_link_that_holds_no_file_is_never_fetched() -> None:
    # 6 of the 12 Semantic Scholar links of the day 1 pool were doi.org
    # addresses. doi.org is a lookup key and never a fetch target.
    asked: list = []

    result = read(
        fields={"open_copy_url": "https://doi.org/10.1000/aaa"},
        resolution=Resolution(found=True, reason=reasons.BLOCKLISTED_ONLY),
        fetch=asks(asked),
    )

    assert result.reason == reasons.BLOCKLISTED_ONLY
    assert result.attempts == 0
    assert asked == []


def test_the_resolve_is_skipped_when_a_paper_has_no_identifier() -> None:
    asked: list = []

    read_open_copy(
        paper(doi="", open_copy_url="https://www.mdpi.com/aaa.pdf"),
        lambda doi: asked.append(doi) or Resolution(found=False),
        lambda url: pdf_bytes(),
        lambda data: extracted(A_LONG_TEXT),
        reason_against_paper_text,
    )

    assert asked == []


def asks(asked: list, answers: dict | None = None):
    """Builds a fetch that records each address and answers from a table."""

    def fetch(url: str):
        asked.append(url)
        answer = (answers or {}).get(url)
        if isinstance(answer, Exception):
            raise answer
        return answer if answer is not None else pdf_bytes()

    return fetch


def test_usable_text_stops_the_attempts() -> None:
    asked: list = []

    result = read(resolution=FOUND_BOTH, fetch=asks(asked))

    assert asked == [REPOSITORY_COPY.url]
    assert result.attempts == 1


def test_a_second_candidate_is_tried_after_a_refusal() -> None:
    # 10 Papers of the measured pool carry a free file, and the old rule
    # reached 5, because it offered one location and stopped.
    asked: list = []

    result = read(
        resolution=FOUND_BOTH,
        fetch=asks(asked, {REPOSITORY_COPY.url: refused(reasons.FETCH_REFUSED)}),
    )

    assert asked == [REPOSITORY_COPY.url, JOURNAL_COPY.url]
    assert result.reason == reasons.USABLE
    assert result.open_copy == JOURNAL_COPY
    assert result.attempts == 2


def test_a_text_that_fails_a_check_tries_the_next_candidate() -> None:
    # The candidates are three files of one article, and the checks test the
    # file. A scan of paper pages extracts to nonsense, and the next candidate
    # can be the publisher file that extracts cleanly.
    asked: list = []

    def extract(data: bytes) -> Extracted:
        return extracted(A_SHORT_TEXT if len(asked) == 1 else A_LONG_TEXT)

    result = read(resolution=FOUND_BOTH, fetch=asks(asked), extract=extract)

    assert asked == [REPOSITORY_COPY.url, JOURNAL_COPY.url]
    assert result.reason == reasons.USABLE
    assert result.open_copy == JOURNAL_COPY
    assert result.attempts == 2


def test_the_last_failed_text_is_the_answer_when_every_file_fails() -> None:
    asked: list = []

    result = read(resolution=FOUND_BOTH, fetch=asks(asked), text=A_SHORT_TEXT)

    assert asked == [REPOSITORY_COPY.url, JOURNAL_COPY.url]
    assert result.reason == reasons.TEXT_TOO_SHORT
    assert result.tried_hosts == ("dro.dur.ac.uk", "www.mdpi.com")


def test_a_failed_text_beats_a_later_refusal_as_the_reason() -> None:
    # The pipeline got one step further with the file than with the 403, and
    # the reason table counts the step a Paper reached.
    result = read(
        resolution=FOUND_BOTH,
        fetch=asks([], {JOURNAL_COPY.url: refused(reasons.FETCH_REFUSED)}),
        text="energy " * 2000,
    )

    assert result.reason == reasons.NO_SECTION_WORD
    assert result.open_copy == REPOSITORY_COPY
    assert result.attempts == 2


def test_the_last_refusal_is_the_reason_when_every_candidate_fails() -> None:
    result = read(
        resolution=FOUND_BOTH,
        fetch=asks(
            [],
            {
                REPOSITORY_COPY.url: refused(reasons.FETCH_REFUSED),
                JOURNAL_COPY.url: refused(reasons.NOT_A_PDF, status=200),
            },
        ),
    )

    assert result.reason == reasons.NOT_A_PDF
    assert result.open_copy == JOURNAL_COPY
    assert result.attempts == 2


def test_a_host_that_times_out_does_not_lose_the_other_candidates() -> None:
    # A timeout raises, and the old loop let it out, so a slow repository
    # cost the Paper a file that sat at the second candidate.
    asked: list = []
    slow = FetchFailed("dro.dur.ac.uk did not answer twice in a row.")

    result = read(resolution=FOUND_BOTH, fetch=asks(asked, {REPOSITORY_COPY.url: slow}))

    assert asked == [REPOSITORY_COPY.url, JOURNAL_COPY.url]
    assert result.reason == reasons.USABLE
    assert result.tried_hosts == ("dro.dur.ac.uk", "www.mdpi.com")


def test_a_refusal_wins_over_a_timeout_as_the_reason() -> None:
    # One host refused with an answer and one failed to answer. The table
    # counts the answer, because a refusal is a fact about a host.
    slow = FetchFailed("dro.dur.ac.uk did not answer twice in a row.")

    result = read(
        resolution=FOUND_BOTH,
        fetch=asks(
            [],
            {
                REPOSITORY_COPY.url: slow,
                JOURNAL_COPY.url: refused(reasons.FETCH_REFUSED),
            },
        ),
    )

    assert result.reason == reasons.FETCH_REFUSED
    assert result.attempts == 2


def test_a_paper_whose_every_candidate_times_out_still_breaks() -> None:
    # A failure is not an answer. Nothing of it is cached, and the command
    # counts the Paper as dropped instead of printing a reason it never got.
    def fetch(url: str):
        raise FetchFailed("Neither host answered twice in a row.")

    with pytest.raises(FetchFailed):
        read(resolution=FOUND_BOTH, fetch=fetch)


def test_a_resolver_that_names_no_reason_still_lands_in_the_table() -> None:
    assert read(resolution=Resolution(found=True)).reason in reasons.ALL

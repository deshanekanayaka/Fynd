"""The pipeline has to reach every reason, and reach them with no HTTP."""

import pytest

from fynd import reasons
from fynd.extract import Extracted
from fynd.fetcher import Fetched, FetchFailed, Refused
from fynd.models import OpenCopy, Paper
from fynd.open_copy import read_open_copy
from fynd.openalex import Resolution
from fynd.source_text import (
    MIN_CHARACTERS,
    reason_against_page_text,
    reason_against_paper_text,
)

A_LONG_TEXT = "Results. The household energy demand of England rose again. " * 200
REPOSITORY_COPY = OpenCopy(
    url="https://dro.dur.ac.uk/aaa.pdf", host="dro.dur.ac.uk", license="cc-by"
)
JOURNAL_COPY = OpenCopy(
    url="https://www.mdpi.com/aaa.pdf", host="www.mdpi.com", license="cc-by"
)


def paper(**fields) -> Paper:
    """Builds a Paper with the fields a test cares about."""
    values = {"paper_id": "aaa", "title": "A paper", "doi": "10.1000/aaa"}
    values.update(fields)
    return Paper(**values)


def resolve_to(answer: Resolution):
    def resolve(doi: str) -> Resolution:
        return answer

    return resolve


def fetch_to(answer):
    def fetch(url: str):
        return answer

    return fetch


def extract_to(text: str):
    def extract(data: bytes) -> Extracted:
        return Extracted(text=text, extractor="pdfplumber 0.11.10", structure=[])

    return extract


def pdf_bytes() -> Fetched:
    return Fetched(data=b"%PDF-1.7", content_type="application/pdf")


def test_a_paper_that_reaches_usable_text() -> None:
    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=True, candidates=(REPOSITORY_COPY,))),
        fetch_to(pdf_bytes()),
        extract_to(A_LONG_TEXT),
        reason_against_paper_text,
    )

    assert result.reason == reasons.USABLE
    assert result.is_usable is True
    assert result.attempts == 1
    assert result.open_copy == REPOSITORY_COPY
    assert result.extracted is not None
    assert result.extracted.text == A_LONG_TEXT


def test_a_paper_with_no_identifier_and_no_link() -> None:
    result = read_open_copy(
        paper(doi=""),
        resolve_to(Resolution(found=False, reason=reasons.NO_OPENALEX_RECORD)),
        fetch_to(pdf_bytes()),
        extract_to(A_LONG_TEXT),
        reason_against_paper_text,
    )
    assert result.reason == reasons.NO_DOI


def test_a_paper_openalex_never_heard_of() -> None:
    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=False, reason=reasons.NO_OPENALEX_RECORD)),
        fetch_to(pdf_bytes()),
        extract_to(A_LONG_TEXT),
        reason_against_paper_text,
    )
    assert result.reason == reasons.NO_OPENALEX_RECORD


def test_a_paper_with_only_a_publisher_location() -> None:
    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=True, reason=reasons.NO_OPEN_LOCATION)),
        fetch_to(pdf_bytes()),
        extract_to(A_LONG_TEXT),
        reason_against_paper_text,
    )
    assert result.reason == reasons.NO_OPEN_LOCATION


def test_the_semantic_scholar_link_is_the_last_resort() -> None:
    result = read_open_copy(
        paper(open_copy_url="https://www.mdpi.com/aaa.pdf"),
        resolve_to(Resolution(found=True, reason=reasons.NO_OPEN_LOCATION)),
        fetch_to(pdf_bytes()),
        extract_to(A_LONG_TEXT),
        reason_against_paper_text,
    )

    assert result.reason == reasons.USABLE
    assert result.open_copy is not None
    assert result.open_copy.host == "www.mdpi.com"
    assert result.open_copy.license == ""


def test_a_doi_org_link_is_never_a_fetch_target() -> None:
    # 6 of the 12 links in the first live run were this. A doi.org link is a
    # redirect to a publisher page, and ADR 0007 fetches no publisher.
    result = read_open_copy(
        paper(open_copy_url="https://doi.org/10.1000/aaa"),
        resolve_to(Resolution(found=True, reason=reasons.NO_OPEN_LOCATION)),
        fetch_to(pdf_bytes()),
        extract_to(A_LONG_TEXT),
        reason_against_paper_text,
    )
    assert result.reason == reasons.NO_OPEN_LOCATION


def test_a_refused_fetch_keeps_its_reason() -> None:
    refused = Refused(status=403, content_type="text/html", reason=reasons.FETCH_REFUSED)
    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=True, candidates=(REPOSITORY_COPY,))),
        fetch_to(refused),
        extract_to(A_LONG_TEXT),
        reason_against_paper_text,
    )

    assert result.reason == reasons.FETCH_REFUSED
    assert result.open_copy == REPOSITORY_COPY
    assert result.extracted is None


def test_a_page_that_is_not_a_pdf_keeps_its_reason() -> None:
    refused = Refused(status=200, content_type="text/html", reason=reasons.NOT_A_PDF)
    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=True, candidates=(REPOSITORY_COPY,))),
        fetch_to(refused),
        extract_to(A_LONG_TEXT),
        reason_against_paper_text,
    )
    assert result.reason == reasons.NOT_A_PDF


def test_a_short_text_is_not_usable() -> None:
    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=True, candidates=(REPOSITORY_COPY,))),
        fetch_to(pdf_bytes()),
        extract_to("Please accept our cookies to continue."),
        reason_against_paper_text,
    )
    assert result.reason == reasons.TEXT_TOO_SHORT


def test_a_text_of_rubbish_is_not_usable() -> None:
    # Two control characters and two private use glyphs, which is what a
    # badly extracted PDF returns.
    rubbish = (chr(1) + chr(2) + chr(0xE000) + chr(0xE001)) * 2000
    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=True, candidates=(REPOSITORY_COPY,))),
        fetch_to(pdf_bytes()),
        extract_to(rubbish),
        reason_against_paper_text,
    )
    assert result.reason == reasons.TEXT_NOT_TEXTUAL


def test_the_resolve_is_skipped_when_a_paper_has_no_identifier() -> None:
    asked: list = []

    def resolve(doi: str) -> Resolution:
        asked.append(doi)
        return Resolution(found=False, reason=reasons.NO_OPENALEX_RECORD)

    read_open_copy(
        paper(doi="", open_copy_url="https://www.mdpi.com/aaa.pdf"),
        resolve,
        fetch_to(pdf_bytes()),
        extract_to(A_LONG_TEXT),
        reason_against_paper_text,
    )
    assert asked == []


def test_every_reason_is_a_name_the_table_prints() -> None:
    # The reason table counts these strings, so a typo must fail a test and not
    # a table.
    for reason in (
        reasons.USABLE,
        reasons.NO_DOI,
        reasons.NO_OPENALEX_RECORD,
        reasons.NO_OPEN_LOCATION,
        reasons.NO_PDF_LINK,
        reasons.BLOCKLISTED_ONLY,
        reasons.FETCH_REFUSED,
        reasons.NOT_A_PDF,
        reasons.TEXT_TOO_SHORT,
        reasons.TEXT_NOT_TEXTUAL,
        reasons.NO_SECTION_WORD,
    ):
        assert reason in reasons.ALL
    assert len(reasons.ALL) == 11
    assert not hasattr(reasons, "NO_REPOSITORY_LOCATION")


def test_a_text_at_the_length_threshold() -> None:
    # The text holds a section word, so only the length decides.
    short = "results " + "a" * (MIN_CHARACTERS - 9)
    assert len(short) == MIN_CHARACTERS - 1
    assert reason_against_paper_text(short) == reasons.TEXT_TOO_SHORT
    assert reason_against_paper_text(short + "a") == ""


def test_a_paper_text_with_no_section_word_is_refused() -> None:
    # A repository landing page is long and holds no section word. The 5 Papers
    # of the live run of 2026-10-09 all hold method, results and references.
    assert reason_against_paper_text("energy " * 2000) == reasons.NO_SECTION_WORD
    assert reason_against_page_text("energy " * 2000) == ""


def test_a_text_at_the_ordinary_share_boundary() -> None:
    # 0.95 of the characters must be ordinary. Every real text of the live run
    # scored above 0.996, and the old value of 0.80 passed a text that was one
    # fifth rubbish.
    assert reason_against_page_text("a" * 9600 + chr(0xE000) * 400) == ""
    assert (
        reason_against_page_text("a" * 9000 + chr(0xE000) * 1000) == reasons.TEXT_NOT_TEXTUAL
    )


def test_the_semantic_scholar_link_is_not_used_when_openalex_names_one() -> None:
    # The fallback produced none of the 5 usable files of 2026-10-09 and cost
    # 3 refused fetches, so it runs only when OpenAlex names no candidate.
    asked: list = []

    def fetch(url: str):
        asked.append(url)
        return pdf_bytes()

    read_open_copy(
        paper(open_copy_url="https://doaj.org/article/aaa"),
        resolve_to(Resolution(found=True, candidates=(REPOSITORY_COPY,))),
        fetch,
        extract_to(A_LONG_TEXT),
        reason_against_paper_text,
    )

    assert asked == [REPOSITORY_COPY.url]


def test_a_second_candidate_is_tried_after_a_refusal() -> None:
    # 10 Papers of the measured pool carry a free file, and the old rule
    # reached 5, because it offered one location and stopped.
    asked: list = []

    def fetch(url: str):
        asked.append(url)
        if url == REPOSITORY_COPY.url:
            return Refused(status=403, content_type="text/html", reason=reasons.FETCH_REFUSED)
        return pdf_bytes()

    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=True, candidates=(REPOSITORY_COPY, JOURNAL_COPY))),
        fetch,
        extract_to(A_LONG_TEXT),
        reason_against_paper_text,
    )

    assert asked == [REPOSITORY_COPY.url, JOURNAL_COPY.url]
    assert result.reason == reasons.USABLE
    assert result.open_copy == JOURNAL_COPY
    assert result.attempts == 2


def test_the_first_file_stops_the_attempts() -> None:
    asked: list = []

    def fetch(url: str):
        asked.append(url)
        return pdf_bytes()

    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=True, candidates=(REPOSITORY_COPY, JOURNAL_COPY))),
        fetch,
        extract_to(A_LONG_TEXT),
        reason_against_paper_text,
    )

    assert asked == [REPOSITORY_COPY.url]
    assert result.attempts == 1


def test_a_text_that_fails_a_check_stops_the_attempts() -> None:
    # A file arrived, so the Paper has its answer. A second candidate of the
    # same Paper is the same article, and the reason table counts the failure.
    asked: list = []

    def fetch(url: str):
        asked.append(url)
        return pdf_bytes()

    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=True, candidates=(REPOSITORY_COPY, JOURNAL_COPY))),
        fetch,
        extract_to("Please accept our cookies to continue."),
        reason_against_paper_text,
    )

    assert asked == [REPOSITORY_COPY.url]
    assert result.reason == reasons.TEXT_TOO_SHORT


def test_the_last_refusal_is_the_reason_when_every_candidate_fails() -> None:
    def fetch(url: str):
        if url == REPOSITORY_COPY.url:
            return Refused(status=403, content_type="text/html", reason=reasons.FETCH_REFUSED)
        return Refused(status=200, content_type="text/html", reason=reasons.NOT_A_PDF)

    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=True, candidates=(REPOSITORY_COPY, JOURNAL_COPY))),
        fetch,
        extract_to(A_LONG_TEXT),
        reason_against_paper_text,
    )

    assert result.reason == reasons.NOT_A_PDF
    assert result.open_copy == JOURNAL_COPY
    assert result.attempts == 2


def test_a_fallback_link_that_holds_no_file_is_never_fetched() -> None:
    # 6 of the 12 Semantic Scholar links of the day 1 pool were doi.org
    # addresses. doi.org is a lookup key and never a fetch target.
    asked: list = []

    def fetch(url: str):
        asked.append(url)
        return pdf_bytes()

    result = read_open_copy(
        paper(open_copy_url="https://doi.org/10.1000/aaa"),
        resolve_to(Resolution(found=True, reason=reasons.BLOCKLISTED_ONLY)),
        fetch,
        extract_to(A_LONG_TEXT),
        reason_against_paper_text,
    )

    assert result.reason == reasons.BLOCKLISTED_ONLY
    assert result.attempts == 0
    assert asked == []


def test_a_landing_page_only_paper_keeps_its_reason() -> None:
    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=True, reason=reasons.NO_PDF_LINK)),
        fetch_to(pdf_bytes()),
        extract_to(A_LONG_TEXT),
        reason_against_paper_text,
    )
    assert result.reason == reasons.NO_PDF_LINK


def test_a_host_that_times_out_does_not_lose_the_other_candidates() -> None:
    # A timeout raises, and the old loop let it out, so a slow repository
    # cost the Paper a file that sat at the second candidate.
    asked: list = []

    def fetch(url: str):
        asked.append(url)
        if url == REPOSITORY_COPY.url:
            raise FetchFailed("dro.dur.ac.uk did not answer twice in a row.")
        return pdf_bytes()

    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=True, candidates=(REPOSITORY_COPY, JOURNAL_COPY))),
        fetch,
        extract_to(A_LONG_TEXT),
        reason_against_paper_text,
    )

    assert asked == [REPOSITORY_COPY.url, JOURNAL_COPY.url]
    assert result.reason == reasons.USABLE
    assert result.tried_hosts == ("dro.dur.ac.uk", "www.mdpi.com")


def test_a_paper_whose_every_candidate_times_out_still_breaks() -> None:
    # A failure is not an answer. Nothing of it is cached, and the command
    # counts the Paper as dropped instead of printing a reason it never got.
    def fetch(url: str):
        raise FetchFailed("Neither host answered twice in a row.")

    with pytest.raises(FetchFailed):
        read_open_copy(
            paper(),
            resolve_to(Resolution(found=True, candidates=(REPOSITORY_COPY, JOURNAL_COPY))),
            fetch,
            extract_to(A_LONG_TEXT),
            reason_against_paper_text,
        )


def test_a_refusal_wins_over_a_timeout_as_the_reason() -> None:
    # One host refused with an answer and one failed to answer. The table
    # counts the answer, because a refusal is a fact about a host.
    def fetch(url: str):
        if url == REPOSITORY_COPY.url:
            raise FetchFailed("dro.dur.ac.uk did not answer twice in a row.")
        return Refused(status=403, content_type="text/html", reason=reasons.FETCH_REFUSED)

    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=True, candidates=(REPOSITORY_COPY, JOURNAL_COPY))),
        fetch,
        extract_to(A_LONG_TEXT),
        reason_against_paper_text,
    )

    assert result.reason == reasons.FETCH_REFUSED
    assert result.attempts == 2


def test_a_resolver_that_names_no_reason_still_lands_in_the_table() -> None:
    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=True)),
        fetch_to(pdf_bytes()),
        extract_to(A_LONG_TEXT),
        reason_against_paper_text,
    )
    assert result.reason in reasons.ALL

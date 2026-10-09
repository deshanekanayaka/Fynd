"""The pipeline has to reach all eight reasons, and reach them with no HTTP."""

from fynd import reasons
from fynd.extract import Extracted
from fynd.fetcher import Fetched, Refused
from fynd.models import OpenCopy, Paper
from fynd.open_copy import read_open_copy
from fynd.openalex import Resolution
from fynd.source_text import MIN_CHARACTERS, reason_against

A_LONG_TEXT = "The household energy demand of England rose again. " * 200
REPOSITORY_COPY = OpenCopy(
    url="https://dro.dur.ac.uk/aaa.pdf", host="dro.dur.ac.uk", license="cc-by"
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
        resolve_to(Resolution(found=True, open_copy=REPOSITORY_COPY)),
        fetch_to(pdf_bytes()),
        extract_to(A_LONG_TEXT),
        reason_against,
    )

    assert result.reason == reasons.USABLE
    assert result.is_usable is True
    assert result.open_copy == REPOSITORY_COPY
    assert result.extracted is not None
    assert result.extracted.text == A_LONG_TEXT


def test_a_paper_with_no_identifier_and_no_link() -> None:
    result = read_open_copy(
        paper(doi=""),
        resolve_to(Resolution(found=False, open_copy=None)),
        fetch_to(pdf_bytes()),
        extract_to(A_LONG_TEXT),
        reason_against,
    )
    assert result.reason == reasons.NO_DOI


def test_a_paper_openalex_never_heard_of() -> None:
    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=False, open_copy=None)),
        fetch_to(pdf_bytes()),
        extract_to(A_LONG_TEXT),
        reason_against,
    )
    assert result.reason == reasons.NO_OPENALEX_RECORD


def test_a_paper_with_only_a_publisher_location() -> None:
    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=True, open_copy=None)),
        fetch_to(pdf_bytes()),
        extract_to(A_LONG_TEXT),
        reason_against,
    )
    assert result.reason == reasons.NO_REPOSITORY_LOCATION


def test_the_semantic_scholar_link_is_the_second_chance() -> None:
    result = read_open_copy(
        paper(open_copy_url="https://www.mdpi.com/aaa.pdf"),
        resolve_to(Resolution(found=True, open_copy=None)),
        fetch_to(pdf_bytes()),
        extract_to(A_LONG_TEXT),
        reason_against,
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
        resolve_to(Resolution(found=True, open_copy=None)),
        fetch_to(pdf_bytes()),
        extract_to(A_LONG_TEXT),
        reason_against,
    )
    assert result.reason == reasons.NO_REPOSITORY_LOCATION


def test_a_refused_fetch_keeps_its_reason() -> None:
    refused = Refused(status=403, content_type="text/html", reason=reasons.FETCH_REFUSED)
    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=True, open_copy=REPOSITORY_COPY)),
        fetch_to(refused),
        extract_to(A_LONG_TEXT),
        reason_against,
    )

    assert result.reason == reasons.FETCH_REFUSED
    assert result.open_copy == REPOSITORY_COPY
    assert result.extracted is None


def test_a_page_that_is_not_a_pdf_keeps_its_reason() -> None:
    refused = Refused(status=200, content_type="text/html", reason=reasons.NOT_A_PDF)
    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=True, open_copy=REPOSITORY_COPY)),
        fetch_to(refused),
        extract_to(A_LONG_TEXT),
        reason_against,
    )
    assert result.reason == reasons.NOT_A_PDF


def test_a_short_text_is_not_usable() -> None:
    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=True, open_copy=REPOSITORY_COPY)),
        fetch_to(pdf_bytes()),
        extract_to("Please accept our cookies to continue."),
        reason_against,
    )
    assert result.reason == reasons.TEXT_TOO_SHORT


def test_a_text_of_rubbish_is_not_usable() -> None:
    # Two control characters and two private use glyphs, which is what a
    # badly extracted PDF returns.
    rubbish = (chr(1) + chr(2) + chr(0xE000) + chr(0xE001)) * 2000
    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=True, open_copy=REPOSITORY_COPY)),
        fetch_to(pdf_bytes()),
        extract_to(rubbish),
        reason_against,
    )
    assert result.reason == reasons.TEXT_NOT_TEXTUAL


def test_the_resolve_is_skipped_when_a_paper_has_no_identifier() -> None:
    asked: list = []

    def resolve(doi: str) -> Resolution:
        asked.append(doi)
        return Resolution(found=False, open_copy=None)

    read_open_copy(
        paper(doi="", open_copy_url="https://www.mdpi.com/aaa.pdf"),
        resolve,
        fetch_to(pdf_bytes()),
        extract_to(A_LONG_TEXT),
        reason_against,
    )
    assert asked == []


def test_every_reason_is_one_of_the_eight() -> None:
    # The reason table counts these strings, so a typo must fail a test and not
    # a table.
    for reason in (
        reasons.USABLE,
        reasons.NO_DOI,
        reasons.NO_OPENALEX_RECORD,
        reasons.NO_REPOSITORY_LOCATION,
        reasons.FETCH_REFUSED,
        reasons.NOT_A_PDF,
        reasons.TEXT_TOO_SHORT,
        reasons.TEXT_NOT_TEXTUAL,
    ):
        assert reason in reasons.ALL
    assert len(reasons.ALL) == 8


def test_a_text_at_the_threshold_is_usable() -> None:
    assert reason_against("a" * (MIN_CHARACTERS - 1)) == reasons.TEXT_TOO_SHORT
    assert reason_against("a" * MIN_CHARACTERS) == ""


def test_a_text_at_the_ordinary_share_boundary() -> None:
    # Four fifths ordinary passes, and anything below it does not.
    ordinary = "a" * 8000
    rubbish = chr(0xE000) * 2000
    assert reason_against(ordinary + rubbish) == ""
    assert reason_against("a" * 7000 + chr(0xE000) * 3000) == reasons.TEXT_NOT_TEXTUAL


def test_an_openalex_location_on_doi_org_is_never_fetched() -> None:
    # The live run of 2026-10-09 found a work whose repository location was a
    # doi.org address. ADR 0007 fetches no publisher, and that host redirects
    # to one, so the guard belongs on every location and not on the fallback.
    asked: list = []

    def fetch(url: str):
        asked.append(url)
        return pdf_bytes()

    lookup_only = OpenCopy(url="https://doi.org/10.1000/aaa", host="doi.org", license="cc-by")
    result = read_open_copy(
        paper(),
        resolve_to(Resolution(found=True, open_copy=lookup_only)),
        fetch,
        extract_to(A_LONG_TEXT),
        reason_against,
    )

    assert result.reason == reasons.NO_REPOSITORY_LOCATION
    assert asked == []

"""The measurement has to count every reason, and name every host."""

import datetime as dt

from fynd import reasons
from fynd.extract import Extracted
from fynd.measure import NO_HOST, host_rows, reason_counts, report
from fynd.models import OpenCopy, Paper
from fynd.open_copy import OpenCopyResult

TODAY = dt.date(2026, 10, 9)


def result(reason: str, host: str = "", characters: int = 0, year: int = 2024) -> OpenCopyResult:
    """Builds one pipeline result, as the measurement reads it."""
    copy = OpenCopy(url=f"https://{host}/aaa.pdf", host=host, license="cc-by") if host else None
    extracted = None
    if characters:
        extracted = Extracted(text="a" * characters, extractor="pdfplumber 0.11.10", structure=[])
    return OpenCopyResult(
        paper=Paper(paper_id="aaa", title="A paper about households", year=year),
        reason=reason,
        open_copy=copy,
        extracted=extracted,
    )


def test_a_host_row_counts_the_links_the_files_and_the_usable_texts() -> None:
    results = [
        result(reasons.USABLE, "dro.dur.ac.uk", characters=9000),
        result(reasons.TEXT_TOO_SHORT, "dro.dur.ac.uk", characters=400),
        result(reasons.FETCH_REFUSED, "dro.dur.ac.uk"),
    ]

    rows = host_rows(results)

    assert rows == [{"host": "dro.dur.ac.uk", "tried": 3, "files": 2, "usable": 1}]


def test_a_paper_with_no_link_gets_its_own_row() -> None:
    rows = host_rows([result(reasons.NO_DOI)])
    assert rows[0]["host"] == NO_HOST


def test_every_reason_is_counted_including_the_ones_at_zero() -> None:
    # The count of a reason nobody hit is the number that says the pipeline
    # never reached that step, which is the first thing a reader asks.
    counts = reason_counts([result(reasons.USABLE, "www.mdpi.com", characters=9000)])

    assert counts[reasons.USABLE] == 1
    assert counts[reasons.NOT_A_PDF] == 0
    assert len(counts) == 9


def test_the_report_holds_the_three_tables_and_the_query() -> None:
    results = [
        result(reasons.USABLE, "dro.dur.ac.uk", characters=9000),
        result(reasons.NOT_A_PDF, "www.sciencedirect.com"),
        result(reasons.NO_DOI),
    ]

    text = report(results, "United Kingdom household energy forecasting", 2022, TODAY)

    assert "United Kingdom household energy forecasting" in text
    assert "from 2022 onward" in text
    assert "2026-10-09" in text
    assert "## By host" in text
    assert "## By reason" in text
    assert "## By Paper" in text
    assert "1 of 3 Papers reached Usable text, which is 33%" in text
    assert "dro.dur.ac.uk" in text
    assert NO_HOST in text


def test_the_report_says_the_files_are_not_in_git() -> None:
    text = report([result(reasons.USABLE, "www.mdpi.com", characters=9000)], "a query", 2022, TODAY)
    assert "not in git" in text


def test_a_title_with_a_pipe_does_not_break_the_table() -> None:
    one = result(reasons.USABLE, "www.mdpi.com", characters=9000)
    broken = OpenCopyResult(
        paper=Paper(paper_id="bbb", title="Energy | demand", year=2023),
        reason=one.reason,
        open_copy=one.open_copy,
        extracted=one.extracted,
    )

    text = report([broken], "a query", 2022, TODAY)

    assert "Energy   demand" in text
    assert "Energy | demand" not in text


def test_an_empty_pool_still_writes_a_file() -> None:
    text = report([], "a query", 2022, TODAY)
    assert "0 of 0 Papers reached Usable text, which is -" in text

"""The measurement has to count every reason, and name every host."""

import datetime as dt

from fynd import reasons
from fynd.extract import Extracted
from fynd.measure import NO_HOST, host_rows, readme_with, reason_counts, report
from fynd.models import OpenCopy, Paper
from fynd.open_copy import OpenCopyResult

TODAY = dt.date(2026, 10, 9)


def result(
    reason: str,
    host: str = "",
    characters: int = 0,
    year: int = 2024,
    tried: tuple[str, ...] = (),
) -> OpenCopyResult:
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
        tried_hosts=tried or ((host,) if host else ()),
    )


def test_every_host_a_paper_tried_counts_a_link() -> None:
    # One Paper tries up to 3 links since ADR 0012. A table that counted one
    # link for each Paper would hide the 403 that sent it to the second host,
    # under a column header that reads "Links tried".
    results = [
        result(
            reasons.USABLE,
            "www.mdpi.com",
            characters=9000,
            tried=("dro.dur.ac.uk", "www.mdpi.com"),
        )
    ]

    rows = host_rows(results)

    assert rows == [
        {"host": "dro.dur.ac.uk", "tried": 1, "files": 0, "usable": 0},
        {"host": "www.mdpi.com", "tried": 1, "files": 1, "usable": 1},
    ]


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
    assert len(counts) == len(reasons.ALL)


def test_the_report_holds_the_three_tables_and_the_query() -> None:
    results = [
        result(reasons.USABLE, "dro.dur.ac.uk", characters=9000),
        result(reasons.NOT_A_PDF, "www.sciencedirect.com"),
        result(reasons.NO_DOI),
    ]

    text = report(
        results,
        query="United Kingdom household energy forecasting",
        year_from=2022,
        limit=20,
        today=TODAY,
    )

    assert "United Kingdom household energy forecasting" in text
    assert "from 2022 onward" in text
    assert "2026-10-09" in text
    assert "## By host" in text
    assert "## By reason" in text
    assert "## By Paper" in text
    assert "limit 20" in text
    assert "1 of 3 Papers reached Usable text, which is 33%" in text
    assert "dro.dur.ac.uk" in text
    # A Paper with no link is counted in a sentence and not as a host row. The
    # per Paper table below still names it, because that table is one row for
    # one Paper.
    host_table = text[text.index("## By host") : text.index("## By reason")]
    assert f"| {NO_HOST} |" not in host_table
    assert "1 Papers never reached a link" in host_table
    assert f"| {NO_HOST} |" in text[text.index("## By Paper") :]


def test_the_report_says_the_files_are_not_in_git() -> None:
    text = report(
        [result(reasons.USABLE, "www.mdpi.com", characters=9000)],
        query="a query",
        year_from=2022,
        limit=20,
        today=TODAY,
    )
    assert "not in git" in text


def test_a_title_with_a_pipe_does_not_break_the_table() -> None:
    one = result(reasons.USABLE, "www.mdpi.com", characters=9000)
    broken = OpenCopyResult(
        paper=Paper(paper_id="bbb", title="Energy | demand", year=2023),
        reason=one.reason,
        open_copy=one.open_copy,
        extracted=one.extracted,
    )

    text = report([broken], query="a query", year_from=2022, limit=20, today=TODAY)

    assert "Energy   demand" in text
    assert "Energy | demand" not in text


def test_an_empty_pool_still_writes_a_file() -> None:
    text = report([], query="a query", year_from=2022, limit=20, today=TODAY)
    assert "0 of 0 Papers reached Usable text, which is -" in text


def test_the_by_paper_table_names_the_attempts() -> None:
    tried_two = ("doaj.org", "www.mdpi.com")
    text = report(
        [result(reasons.USABLE, "www.mdpi.com", characters=9000, tried=tried_two)],
        query="a query",
        year_from=2022,
        limit=20,
        today=TODAY,
    )

    header = text[text.index("## By Paper") :]
    assert "| Attempts |" in header
    assert "| 2 |" in header


def test_the_comparison_line_names_the_previous_the_prediction_and_the_new_count() -> None:
    text = report(
        [result(reasons.USABLE, "www.mdpi.com", characters=9000)],
        query="a query",
        year_from=2022,
        limit=20,
        today=TODAY,
        previous=5,
        predicted=10,
    )

    assert "The previous run reached 5 of 20 Papers." in text
    assert "The rule fix predicted 10." in text
    assert "This run reached 1 of 1." in text


def test_the_comparison_line_is_absent_with_nothing_to_compare() -> None:
    text = report(
        [result(reasons.USABLE, "www.mdpi.com", characters=9000)],
        query="a query",
        year_from=2022,
        limit=20,
        today=TODAY,
    )

    assert "previous run" not in text


def test_readme_with_writes_a_header_for_an_empty_file() -> None:
    text = readme_with("", TODAY)
    assert "# The measurement runs" in text
    assert "- [2026-10-09](open-copy-hosts-2026-10-09.md)" in text


def test_readme_with_keeps_the_earlier_lines() -> None:
    first = readme_with("", dt.date(2026, 10, 9))
    second = readme_with(first, dt.date(2026, 10, 17))

    assert "- [2026-10-09](open-copy-hosts-2026-10-09.md)" in second
    assert "- [2026-10-17](open-copy-hosts-2026-10-17.md)" in second


def test_readme_with_does_not_add_the_same_date_twice() -> None:
    first = readme_with("", TODAY)
    second = readme_with(first, TODAY)

    assert second.count("open-copy-hosts-2026-10-09.md") == 1


def test_a_dropped_paper_stays_in_the_denominator() -> None:
    # A run that broke with a rate limit has no reason row, so the file says
    # how many Papers are missing instead of shrinking the pool in silence.
    text = report(
        [result(reasons.USABLE, "www.mdpi.com", characters=9000)],
        query="a query",
        year_from=2022,
        limit=20,
        today=TODAY,
        dropped=2,
    )

    assert "1 of 3 Papers reached Usable text, which is 33%" in text
    assert "2 Papers are missing from the tables below" in text

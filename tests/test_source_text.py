"""The text checks decide whether a downloaded file is worth reading.

These were part of test_open_copy.py, which made that file look as if the
pipeline owned the thresholds. They belong to `fynd.source_text`, and a Paper
file and a web page answer to different rules.
"""

from fynd import reasons
from fynd.source_text import (
    MIN_CHARACTERS,
    reason_against_page_text,
    reason_against_paper_text,
)


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
    # A web page is not a Paper, so the same text passes the page rule.
    assert reason_against_page_text("energy " * 2000) == ""


def test_a_text_at_the_ordinary_share_boundary() -> None:
    # Accept exactly 95%; reject one fewer ordinary character in the same-sized text.
    assert reason_against_page_text("a" * 9500 + chr(0xE000) * 500) == ""
    assert reason_against_page_text("a" * 9499 + chr(0xE000) * 501) == reasons.TEXT_NOT_TEXTUAL


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
        reasons.ROBOTS_REFUSED,
        reasons.FETCH_REFUSED,
        reasons.NOT_A_PDF,
        reasons.TEXT_TOO_SHORT,
        reasons.TEXT_NOT_TEXTUAL,
        reasons.NO_SECTION_WORD,
    ):
        assert reason in reasons.ALL
    # One row per reason, without fixing how many reasons there are.
    assert len(reasons.ALL) == len(set(reasons.ALL))

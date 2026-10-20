"""Grading is the one hand step, so the file it writes has to be exact.

A grade that lands on the wrong Paper is worse than a missing grade, because
nothing downstream can see it. So the writer works from the identifier and
never from the position in a list.
"""

import datetime as dt

import pytest

from fynd.grading import (
    GradeRefused,
    apply_grades,
    grade_counts,
    ungraded,
    worksheet_rows,
)
from fynd.retrieval_set import RetrievalSet, SeedQuery, SetEntry


def a_set(*grades: int | None) -> RetrievalSet:
    return RetrievalSet(
        topic="United Kingdom household energy forecasting",
        reference_date=dt.date(2026, 10, 20),
        search_limit=50,
        per_query=15,
        papers_offered=len(grades),
        shuffle_seed=1,
        queries=[SeedQuery(name="hand", text="a b c", written_by="hand", note="n")],
        entries=[
            SetEntry(paper_id=f"p{number}", title=f"Paper {number}", grade=grade, queries=["hand"])
            for number, grade in enumerate(grades, start=1)
        ],
    )


def test_a_grade_lands_on_the_paper_its_identifier_names() -> None:
    graded = apply_grades(a_set(None, None, None), {"p2": 2, "p1": 0, "p3": 1})
    assert [entry.grade for entry in graded.entries] == [0, 2, 1]


def test_a_grade_for_a_paper_the_set_does_not_hold_is_refused() -> None:
    with pytest.raises(GradeRefused) as refused:
        apply_grades(a_set(None), {"p9": 1})
    assert "p9" in str(refused.value)


def test_a_grade_outside_0_1_2_is_refused_with_the_paper_named() -> None:
    with pytest.raises(GradeRefused) as refused:
        apply_grades(a_set(None), {"p1": 7})
    assert "p1" in str(refused.value)
    assert "7" in str(refused.value)


def test_an_existing_grade_is_not_overwritten_in_silence() -> None:
    # A second grading pass is a re-grade, and a re-grade that quietly replaces
    # the first one hides a disagreement that matters.
    with pytest.raises(GradeRefused) as refused:
        apply_grades(a_set(1), {"p1": 2})
    assert "already" in str(refused.value)


def test_a_grade_that_repeats_the_existing_one_is_allowed() -> None:
    graded = apply_grades(a_set(1), {"p1": 1})
    assert graded.entries[0].grade == 1


def test_the_ungraded_papers_are_named() -> None:
    assert [entry.paper_id for entry in ungraded(a_set(2, None, 0, None))] == ["p2", "p4"]


def test_the_counts_hold_every_grade_and_the_ungraded() -> None:
    assert grade_counts(a_set(2, 2, 1, 0, None)) == {0: 1, 1: 1, 2: 2, None: 1}


def test_a_worksheet_row_names_the_identifier_and_the_title() -> None:
    rows = worksheet_rows(a_set(None, 1))
    assert len(rows) == 2
    assert "p1" in rows[0]
    assert "Paper 1" in rows[0]
    # A Paper that already carries a grade shows it, so a re-grade sees the
    # first answer before it writes a second one.
    assert "1" in rows[1]

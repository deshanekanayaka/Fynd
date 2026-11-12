"""Checks pool construction, reproducible shuffling, and saved Retrieval set fields."""

import datetime as dt
import pathlib

import pytest
from pydantic import ValidationError

from fynd.models import Paper, SearchResult
from fynd.retrieval_set import (
    PER_QUERY,
    SEARCH_LIMIT,
    SEED_QUERIES,
    SET_MAX,
    SET_MIN,
    SHUFFLE_SEED,
    SetEntry,
    SetTooSmall,
    build_set,
    entries_from,
    papers_offered,
    papers_without_abstract,
    pool_papers,
    shuffled,
)
from fynd.stages.stage2 import SEEDED_TOPIC, SEEDED_TOPIC_QUERY

TODAY = dt.date(2026, 10, 20)


def paper(number: int) -> Paper:
    return Paper(
        paper_id=f"p{number}",
        title=f"Paper {number}",
        abstract="An abstract that never enters git.",
        year=2024,
    )


def found(name: str, numbers: range | list[int]) -> tuple[str, SearchResult]:
    papers = [paper(number) for number in numbers]
    return name, SearchResult(query=f"query for {name}", total=len(papers), papers=papers)


def searching(asked: list):
    """Builds a search that answers every query with 20 Papers nobody else returned."""

    def search(query: str, year_from: int, limit: int) -> SearchResult:
        asked.append((query, year_from, limit))
        start = 1000 * len(asked)
        return SearchResult(query=query, papers=[paper(start + number) for number in range(20)])

    return search


def test_an_entry_holds_the_identifier_and_the_title_and_nothing_else() -> None:
    entry = entries_from([found("hand", [1])], per_query=PER_QUERY)[0]

    assert entry.paper_id == "p1"
    assert entry.title == "Paper 1"
    assert entry.grade is None
    # ADR 0011 refuses a committed abstract, and this file enters git. The year
    # is left out because the grading rule says to read the title and the
    # abstract and nothing else.
    assert "abstract" not in entry.model_dump()
    assert "year" not in entry.model_dump()


def test_one_paper_from_two_queries_is_one_entry_that_names_both() -> None:
    entries = entries_from(
        [found("hand", [1, 2]), found("wider", [2, 3])],
        per_query=PER_QUERY,
    )
    assert [entry.paper_id for entry in entries] == ["p1", "p2", "p3"]
    # Which query got there first does not matter. Both found it, so the entry
    # names both, and a reader of the file sees that the two queries agree.
    assert sorted(entries[1].queries) == ["hand", "wider"]


def test_a_query_contributes_only_its_first_papers() -> None:
    # This helper call takes 20 of 50 results; the production builder takes 15.
    entries = entries_from([found("hand", range(1, 51))], per_query=20)
    assert len(entries) == 20
    assert entries[-1].paper_id == "p20"


def test_the_queries_take_turns_so_the_last_one_is_represented() -> None:
    entries = entries_from(
        [found("first", range(1, 21)), found("second", range(100, 120))],
        per_query=20,
        cap=4,
    )
    # Rank 1 of each, then rank 2 of each, and the cap stops it there.
    assert [entry.paper_id for entry in entries] == ["p1", "p100", "p2", "p101"]


def test_the_pool_stops_at_the_cap_and_still_records_every_query() -> None:
    entries = entries_from(
        [found("first", [1, 2, 3]), found("second", [1])],
        per_query=20,
        cap=1,
    )
    assert len(entries) == 1
    # The second query found the same Paper, and that is recorded even though
    # the pool was already full when its turn came.
    assert entries[0].queries == ["first", "second"]


def test_the_same_seed_gives_the_same_order() -> None:
    entries = entries_from([found("hand", range(1, 41))], per_query=40)
    once = [entry.paper_id for entry in shuffled(entries, SHUFFLE_SEED)]
    twice = [entry.paper_id for entry in shuffled(entries, SHUFFLE_SEED)]
    assert once == twice


def test_the_shuffle_loses_the_rank_order() -> None:
    entries = entries_from([found("hand", range(1, 41))], per_query=40)
    ranked = [entry.paper_id for entry in entries]
    assert [entry.paper_id for entry in shuffled(entries, SHUFFLE_SEED)] != ranked


def test_the_set_asks_every_query_for_the_search_limit_inside_the_window() -> None:
    asked: list = []

    built = build_set(searching(asked), reference_date=TODAY)

    assert len(asked) == len(SEED_QUERIES)
    for _, year_from, limit in asked:
        # A 5 year Evidence window in 2026 starts in 2022.
        assert year_from == 2022
        assert limit == SEARCH_LIMIT
    # Every query is for the one Topic, because a Relevance grade only means
    # something against one Topic.
    assert [query.written_by for query in built.queries] == ["hand"] * 4


def test_the_set_records_the_reference_date_and_its_own_limits() -> None:
    built = build_set(searching([]), reference_date=TODAY)

    assert built.reference_date == TODAY
    assert built.per_query == PER_QUERY
    assert built.search_limit == SEARCH_LIMIT
    assert built.topic == "United Kingdom household energy forecasting"
    assert len(built.queries) == 4
    # Four queries contribute 15 distinct Papers each, reaching the 60-Paper cap.
    assert len(built.entries) == SET_MAX


def test_a_set_under_40_papers_stops_the_run() -> None:
    def search(query: str, year_from: int, limit: int) -> SearchResult:
        # Every query returns the same two Papers, so the pool is far too small
        # to grade, and a silent small set would publish a meaningless recall.
        return SearchResult(query=query, papers=[paper(1), paper(2)])

    with pytest.raises(SetTooSmall) as stopped:
        build_set(search, reference_date=TODAY)

    assert "pooled 2 Papers" in str(stopped.value)
    assert str(SET_MIN) in str(stopped.value)
    assert str(SET_MAX) in str(stopped.value)


def test_the_module_reads_no_clock() -> None:
    source = pathlib.Path("src/fynd/retrieval_set.py").read_text(encoding="utf-8")
    # The caller passes the reference date. A clock here would move the
    # Evidence window on 1 January and move the cache key with it, so a
    # published number would stop meaning what it said.
    assert "date.today" not in source
    assert "datetime.now" not in source


def test_a_grade_outside_0_1_2_is_refused() -> None:
    # Reject invalid saved grades before they can reach the metric calculations.
    with pytest.raises(ValidationError):
        SetEntry(paper_id="p1", title="Paper 1", grade=7)


def test_the_set_records_how_many_papers_the_queries_offered() -> None:
    results = [found("first", [1, 2, 3]), found("second", [3, 4])]
    # Four distinct Papers across the two queries, and p3 is in both.
    assert papers_offered(results, per_query=20) == 4
    # The cap keeps fewer than that, and the difference is what the command
    # reports, because a truncated pool changes what a recall number means.
    assert len(entries_from(results, per_query=20, cap=2)) == 2


def with_abstract(paper_id: str, abstract: str) -> Paper:
    return Paper(paper_id=paper_id, title=paper_id, abstract=abstract)


def test_the_pool_holds_the_abstract_the_cache_kept() -> None:
    # A ranking reads the abstract, and the set file in git holds none. The
    # text comes from the cached search reply and goes nowhere else.
    results = [
        ("hand", SearchResult(query="hand", papers=[with_abstract("a1", "An abstract.")])),
        ("wider", SearchResult(query="wider", papers=[with_abstract("b1", "Another.")])),
    ]

    pool = pool_papers(results, per_query=2, keep={"a1", "b1"})

    assert [paper.paper_id for paper in pool] == ["a1", "b1"]
    assert pool[0].abstract == "An abstract."


def test_a_paper_two_queries_both_returned_is_in_the_pool_once() -> None:
    results = [
        ("hand", SearchResult(query="hand", papers=[with_abstract("same", "An abstract.")])),
        ("wider", SearchResult(query="wider", papers=[with_abstract("same", "An abstract.")])),
    ]

    assert len(pool_papers(results, per_query=2, keep={"same"})) == 1


def test_the_pool_leaves_out_a_paper_the_set_never_held() -> None:
    # The ranked pool is the graded pool. A Paper from rank 16 of a query was
    # returned by the search and never graded, so no ranking may score it.
    results = [
        (
            "hand",
            SearchResult(query="hand", papers=[with_abstract("a1", "x"), with_abstract("a2", "y")]),
        )
    ]

    pool = pool_papers(results, per_query=2, keep={"a1"})

    assert [paper.paper_id for paper in pool] == ["a1"]


def test_the_papers_with_no_abstract_are_counted() -> None:
    pool = [with_abstract("a1", "An abstract."), with_abstract("a2", "")]
    assert papers_without_abstract(pool) == 1


def test_the_set_records_the_query_a_ranking_asks_for() -> None:
    # The label names a place and the grading rule throws the place away, so a
    # ranking asks for the subject. The set carries both, and a later run
    # ranks with the string that built it. See ADR 0015.
    built = build_set(searching([]), reference_date=TODAY)

    assert built.topic == SEEDED_TOPIC
    assert built.topic_query == SEEDED_TOPIC_QUERY
    assert "kingdom" not in built.topic_query.lower()

"""The retrieval table has to count recall and nDCG the way it says it does.

Every number here is computed by hand in the test, because a measurement file
that nobody can check is a claim and not a number.
"""

import datetime as dt
import pathlib

from fynd.models import Paper, SearchResult
from fynd.retrieval import document_text
from fynd.retrieval_report import (
    Row,
    dense_rows,
    ndcg_at,
    rate,
    recall_at,
    relevant_ids,
    report,
    rows_from_searches,
    shared_papers,
)

# Four Papers, so the arithmetic is short enough to do on paper.
GRADES = {"two": 2, "one": 1, "zero": 0, "other": 2}

TODAY = dt.date(2026, 10, 21)
SET_FILE = pathlib.PurePosixPath("tests/files/retrieval-set-2026-10-20.json")


def test_a_grade_of_one_or_two_counts_as_relevant() -> None:
    # The grading rule makes 1 a Paper that covers one part of the Topic. A
    # student would still read it, so recall counts it.
    assert relevant_ids(GRADES) == {"two", "one", "other"}


def test_recall_counts_the_relevant_papers_inside_the_cut() -> None:
    ranking = ["zero", "two", "one", "other"]
    assert recall_at(ranking, GRADES, 2) == (1, 3)
    assert recall_at(ranking, GRADES, 4) == (3, 3)


def test_recall_reads_only_the_first_k_places() -> None:
    ranking = ["two", "other", "one", "zero"]
    assert recall_at(ranking, GRADES, 2) == (2, 3)


def test_a_short_ranking_is_not_padded() -> None:
    # One query returned 15 Papers of a pool of 60, so its ranking is shorter
    # than the cut. It reaches what it reaches, and nothing invents a tail.
    assert recall_at(["two"], GRADES, 20) == (1, 3)


def test_a_paper_outside_the_graded_set_counts_as_nothing() -> None:
    # A Paper no grader read cannot be called relevant, and the file states
    # the pool bias that follows from it.
    assert recall_at(["ungraded", "two"], GRADES, 2) == (1, 3)


def test_recall_over_a_pool_with_no_relevant_paper_is_zero_of_zero() -> None:
    assert recall_at(["zero"], {"zero": 0}, 10) == (0, 0)


def test_ndcg_matches_the_sum_computed_by_hand() -> None:
    # The gain is the grade itself, which is the original linear form.
    # DCG  = 2/log2(2) + 0/log2(3) + 1/log2(4) = 2 + 0 + 0.5    = 2.5
    # IDCG = 2/log2(2) + 2/log2(3) + 1/log2(4) = 2 + 1.2618 + 0.5 = 3.7618
    grades = {"two": 2, "zero": 0, "one": 1, "other": 2}
    got = ndcg_at(["two", "zero", "one"], grades, 3)
    assert round(got, 4) == round(2.5 / 3.7618595071429146, 4)


def test_the_best_order_scores_one() -> None:
    grades = {"a": 2, "b": 1, "c": 0}
    assert ndcg_at(["a", "b", "c"], grades, 3) == 1.0


def test_the_worst_order_scores_less_than_the_best() -> None:
    grades = {"a": 2, "b": 1, "c": 0}
    assert ndcg_at(["c", "b", "a"], grades, 3) < ndcg_at(["a", "b", "c"], grades, 3)


def test_ndcg_over_a_pool_with_no_relevant_paper_is_zero() -> None:
    # Nothing to find, so there is no best order to divide by.
    assert ndcg_at(["zero"], {"zero": 0}, 10) == 0.0


def test_a_rate_prints_its_raw_count() -> None:
    assert rate(11, 20) == "55% (11/20)"
    assert rate(0, 0) == "- (0/0)"


def test_the_table_names_every_row_with_its_numbers() -> None:
    rows = [
        Row(name="Baseline", note="The order the four searches arrived in", ranking=["two", "one"]),
        Row(name="hand", note="One query alone", ranking=["zero", "two"]),
    ]

    text = report(
        rows=rows,
        grades=GRADES,
        queries=[("hand", "united kingdom household energy forecasting")],
        reference_date=dt.date(2026, 10, 20),
        today=TODAY,
        set_file=SET_FILE,
        per_query=15,
        shared=0,
        without_abstract=0,
    )

    assert "| Baseline |" in text
    assert "| hand |" in text
    # The headline rate and its raw count, for the baseline row at 20.
    assert "(2/3)" in text


def test_the_table_states_its_three_limits() -> None:
    text = report(
        rows=[Row(name="Baseline", note="", ranking=["two"])],
        grades=GRADES,
        queries=[("hand", "united kingdom household energy forecasting")],
        reference_date=dt.date(2026, 10, 20),
        today=TODAY,
        set_file=SET_FILE,
        per_query=15,
        shared=0,
        without_abstract=0,
    )

    assert "One person wrote every published grade" in text
    assert "Recall over a pool is recall inside the pool" in text
    assert "no constant was tuned" in text


def test_the_table_names_the_queries_and_the_dates() -> None:
    text = report(
        rows=[Row(name="Baseline", note="", ranking=["two"])],
        grades=GRADES,
        queries=[
            ("hand", "united kingdom household energy forecasting"),
            ("wider", "household energy demand forecasting"),
        ],
        reference_date=dt.date(2026, 10, 20),
        today=TODAY,
        set_file=SET_FILE,
        per_query=15,
        shared=0,
        without_abstract=0,
    )

    assert "household energy demand forecasting" in text
    # The reference date of the set and the date of the run are two dates, and
    # the file carries both, because the Evidence window moves on 1 January.
    assert "2026-10-20" in text
    assert "2026-10-21" in text


def search(name: str, paper_ids: list[str]) -> tuple[str, SearchResult]:
    papers = [Paper(paper_id=paper_id, title=paper_id) for paper_id in paper_ids]
    return name, SearchResult(query=name, total=len(papers), papers=papers)


def test_the_baseline_takes_one_rank_from_each_query_in_turn() -> None:
    results = [search("hand", ["a1", "a2"]), search("wider", ["b1", "b2"])]
    graded = {"a1", "a2", "b1", "b2"}

    rows = rows_from_searches(results, per_query=2, pool_size=len(graded))

    assert rows[0].name == "Baseline"
    assert rows[0].ranking == ["a1", "b1", "a2", "b2"]


def test_a_query_row_holds_only_its_own_papers() -> None:
    results = [search("hand", ["a1", "a2"]), search("wider", ["b1"])]
    rows = rows_from_searches(results, per_query=2, pool_size=3)

    assert [row.name for row in rows] == ["Baseline", "hand", "wider"]
    assert rows[1].ranking == ["a1", "a2"]
    assert rows[2].ranking == ["b1"]


def test_a_paper_nobody_graded_keeps_its_place_and_counts_as_nothing() -> None:
    # Dropping it would move the Papers behind it up, so recall would be
    # measured over a ranking that never existed. It stays, and it scores
    # nothing, which is what the published limits say. The command refuses a
    # pool that moved, so this case never reaches a published number.
    results = [search("hand", ["ungraded", "two"])]
    rows = rows_from_searches(results, per_query=2, pool_size=2)

    assert rows[1].ranking == ["ungraded", "two"]
    assert recall_at(rows[1].ranking, GRADES, 1) == (0, 3)
    assert ndcg_at(rows[1].ranking, GRADES, 1) == 0.0


def test_the_shared_papers_of_the_queries_are_counted() -> None:
    both = [search("hand", ["a1", "shared"]), search("wider", ["shared", "b2"])]
    assert shared_papers(both, per_query=2) == 1
    assert shared_papers([search("hand", ["a1"])], per_query=2) == 0


def test_the_table_says_when_no_row_is_a_fynd_ranking() -> None:
    arrival = report(
        rows=[Row(name="Baseline", note="", ranking=["two"])],
        grades=GRADES,
        queries=[("hand", "a query")],
        reference_date=dt.date(2026, 10, 20),
        today=TODAY,
        set_file=SET_FILE,
        per_query=15,
        shared=0,
        without_abstract=0,
    )
    assert "No row below is a ranking of Fynd" in arrival

    # The sentence has to disappear by itself when the first real row arrives,
    # or a later table would publish something untrue.
    with_ranking = report(
        rows=[Row(name="BM25", note="", ranking=["two"], is_fynd_ranking=True, reads_text=True)],
        grades=GRADES,
        queries=[("hand", "a query")],
        reference_date=dt.date(2026, 10, 20),
        today=TODAY,
        set_file=SET_FILE,
        per_query=15,
        shared=0,
        without_abstract=0,
    )
    assert "No row below is a ranking of Fynd" not in with_ranking


def test_the_table_says_the_queries_overlap_when_they_do() -> None:
    text = report(
        rows=[Row(name="Baseline", note="", ranking=["two"])],
        grades=GRADES,
        queries=[("hand", "a query")],
        reference_date=dt.date(2026, 10, 20),
        today=TODAY,
        set_file=SET_FILE,
        per_query=15,
        shared=3,
        without_abstract=0,
    )
    assert "3 Papers were returned by more than one query" in text
    assert "share no Paper at all" not in text


def test_the_table_counts_the_papers_with_no_abstract() -> None:
    # BM25 reads the title and the abstract. A Paper with no abstract is
    # ranked on its title alone, and the reader has to know how many.
    text = report(
        rows=[Row(name="BM25", note="", ranking=["two"], is_fynd_ranking=True, reads_text=True)],
        grades=GRADES,
        queries=[("hand", "a query")],
        reference_date=dt.date(2026, 10, 20),
        today=TODAY,
        set_file=SET_FILE,
        per_query=15,
        shared=0,
        without_abstract=8,
    )

    assert "8 Papers of the pool carry no abstract" in text


def test_the_abstract_count_is_left_out_while_no_row_reads_text() -> None:
    text = report(
        rows=[Row(name="Baseline", note="", ranking=["two"])],
        grades=GRADES,
        queries=[("hand", "a query")],
        reference_date=dt.date(2026, 10, 20),
        today=TODAY,
        set_file=SET_FILE,
        per_query=15,
        shared=0,
        without_abstract=8,
    )

    # No row reads an abstract yet, so the sentence would explain nothing.
    assert "no abstract" not in text


def embed_at_size(vectors: dict[int, dict[str, list[float]]], calls: list):
    """Returns a factory of embedding functions, one for each vector size.

    The table ranks the same pool at two sizes, so a test has to see that each
    row asked at its own size and read the vectors that size returned.
    """

    def factory(size: int):
        def embed(texts: list[str], input_type: str) -> list[list[float]]:
            calls.append((size, input_type, texts))
            return [vectors[size][text] for text in texts]

        return embed

    return factory


def test_the_meaning_rows_rank_at_each_size_and_for_each_string() -> None:
    # The label names the place and the query names the subject, and ADR 0015
    # says a ranking reads the query. Both are published, because a table that
    # held only the better one is a configuration chosen after the numbers.
    near = Paper(paper_id="two", title="Household energy forecasting")
    far = Paper(paper_id="zero", title="Ultra-processed food")
    at_1024 = {
        "United Kingdom household energy forecasting": [1.0, 0.0],
        "household energy forecasting": [1.0, 0.0],
        document_text(near): [0.9, 0.1],
        document_text(far): [0.0, 1.0],
    }
    # At 512 the two Papers swap, so a row that read the wrong size is visible.
    at_512 = dict(at_1024)
    at_512[document_text(near)] = [0.0, 1.0]
    at_512[document_text(far)] = [0.9, 0.1]
    calls: list = []

    rows = dense_rows(
        [
            ("label", "United Kingdom household energy forecasting"),
            ("query", "household energy forecasting"),
        ],
        [far, near],
        embed_at_size({1024: at_1024, 512: at_512}, calls),
        "voyage-test",
        sizes=(1024, 512),
    )

    assert [row.name for row in rows] == [
        "Meaning 1024, label",
        "Meaning 1024, query",
        "Meaning 512, label",
        "Meaning 512, query",
    ]
    assert [row.ranking for row in rows] == [
        ["two", "zero"],
        ["two", "zero"],
        ["zero", "two"],
        ["zero", "two"],
    ]
    assert all(row.is_fynd_ranking and row.reads_text for row in rows)
    # Every call named the size of the row that made it.
    assert {size for size, _, _ in calls} == {1024, 512}


def test_a_meaning_row_names_the_string_it_asked_for() -> None:
    one = Paper(paper_id="two", title="Household energy forecasting")
    vectors = {1024: {"household energy forecasting": [1.0], document_text(one): [1.0]}}
    calls: list = []

    rows = dense_rows(
        [("query", "household energy forecasting")],
        [one],
        embed_at_size(vectors, calls),
        "voyage-test",
        sizes=(1024,),
    )

    assert "`household energy forecasting`" in rows[0].note
    assert "query" in rows[0].note
    # The model is in the row, because a vector of one model says nothing
    # about a vector of another.
    assert "`voyage-test`" in rows[0].note

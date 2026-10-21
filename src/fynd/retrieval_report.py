"""Count how well a ranking ordered the Retrieval set, and write the table.

`PRD.md` names recall at 20 as the metric for retrieval, and 20 is the cut a
Project is built on. So this file turns a ranking and the hand grades into
three numbers, and writes the dated file that publishes them.

The arithmetic is separate from the ranking on purpose. `src/fynd/retrieval.py`
orders Papers and knows nothing about a grade, and this file reads grades and
knows nothing about BM25. A test can then compute every number by hand.

Nothing here reads a clock. The caller passes both dates, because one is the
reference date of the graded set and the other is the day the run happened.
"""

import datetime as dt
import math
import pathlib
from dataclasses import dataclass, field
from typing import Final

from fynd.measure import share
from fynd.models import SearchResult
from fynd.retrieval_set import entries_from

# A grade of 1 or 2 counts as relevant. A 1 covers one part of the Topic, and a
# student would still cite it, so a ranking that found it did its job. See
# docs/retrieval-set-grading-rule.md.
RELEVANT_GRADES: Final = (1, 2)

# The cuts the table reports. 20 is the headline, because 20 is the cut a
# Project is built on. 10 is the column that separates the rows, because 20 of
# 60 Papers reads high for every ranking.
HEADLINE_CUT: Final = 20
SECOND_CUT: Final = 10
NDCG_CUT: Final = 10


# The gain of one Paper is its grade. That is the original linear form of
# Jarvelin and Kekalainen, and it is the default of the scikit-learn function,
# so a reader can reproduce the number. The other published form is 2 to the
# power of the grade, less 1, which would weigh a 2 three times a 1 instead of
# twice. Nothing here is tuned, and this is a stated default and not a choice
# made against the numbers.
def gain_of(grade: int) -> int:
    """Returns the gain nDCG gives one grade, which is the grade itself."""
    return grade


@dataclass(frozen=True)
class Row:
    """One row of the table, which is one ranking of the pool."""

    name: str
    note: str
    # The Papers in rank order. A row may be shorter than the cut, because one
    # query returned 15 Papers of a pool of 60, and a short ranking reaches
    # what it reaches. Nothing pads it.
    ranking: list[str] = field(default_factory=list)
    # Whether a ranking of Fynd produced this row. An arrival order of the
    # search is not one. The file says so while every row is an arrival order,
    # and that sentence disappears by itself when the first real row arrives.
    is_fynd_ranking: bool = False
    # Whether this row read the title and the abstract. A fusion reads places
    # and not text, so the note about the missing abstracts belongs only to the
    # rows the missing text really reaches.
    reads_text: bool = False


def rows_from_searches(
    results: list[tuple[str, SearchResult]], per_query: int, pool_size: int
) -> list[Row]:
    """Returns the baseline row and one row for each query, from the searches.

    The baseline is the order the four searches really arrived in, taken one
    rank at a time from each query. That is the same order the set builder
    pooled them in, so the baseline row is built by the shipped code and not
    by a second rule written for the table.

    A query row holds only the Papers of its own query, and nothing pads it
    with Papers its query never returned.

    `pool_size` is the size of the graded set, which caps the baseline exactly
    as it capped the set when it was built. Nothing is filtered by grade. A
    Paper nobody graded keeps its place and counts as nothing, which is what
    the published limits say, and the caller refuses a pool that moved.
    """
    pooled = entries_from(results, per_query=per_query, cap=pool_size)
    rows = [
        Row(
            name="Baseline",
            note="The four searches as they arrived, one rank at a time",
            ranking=[entry.paper_id for entry in pooled],
        )
    ]
    for name, result in results:
        rows.append(
            Row(
                name=name,
                note=f"The `{name}` query alone, as it arrived",
                ranking=[paper.paper_id for paper in result.papers[:per_query]],
            )
        )
    return rows


def shared_papers(results: list[tuple[str, SearchResult]], per_query: int) -> int:
    """Counts the Papers that more than one query returned.

    The table says whether the queries overlap, and that is a fact of the run
    and never a sentence written once by hand.
    """
    seen: dict[str, int] = {}
    for _, result in results:
        for paper in result.papers[:per_query]:
            seen[paper.paper_id] = seen.get(paper.paper_id, 0) + 1
    return sum(1 for count in seen.values() if count > 1)


def relevant_ids(grades: dict[str, int]) -> set[str]:
    """Returns the Papers that count as relevant."""
    return {paper_id for paper_id, grade in grades.items() if grade in RELEVANT_GRADES}


def recall_at(ranking: list[str], grades: dict[str, int], k: int) -> tuple[int, int]:
    """Returns the relevant Papers inside the first k places, and the total.

    The total is every relevant Paper of the pool and not of the ranking. A
    row that reached 15 Papers of 60 is measured against all 39 relevant ones,
    because the question is what a student gets and not what the row tried.
    """
    relevant = relevant_ids(grades)
    found = sum(1 for paper_id in ranking[:k] if paper_id in relevant)
    return found, len(relevant)


def dcg(gains: list[int]) -> float:
    """Returns the discounted cumulative gain of these gains, in this order.

    A Paper in place 2 is worth its gain divided by the logarithm of 3, so a
    relevant Paper found late counts for less than one found first.
    """
    return sum(gain / math.log2(place + 1) for place, gain in enumerate(gains, start=1))


def ndcg_at(ranking: list[str], grades: dict[str, int], k: int) -> float:
    """Returns the normalised discounted cumulative gain at k.

    The ideal order is the pool's own grades from best to worst, so the number
    is 1.0 only when no better order of this pool exists. A pool with nothing
    relevant in it returns 0.0, because there is no ideal order to divide by.
    """
    # A Paper the ranking holds but nobody graded scores nothing. The file
    # states that as the pool bias.
    gains = [gain_of(grades.get(paper_id, 0)) for paper_id in ranking[:k]]
    ideal = sorted((gain_of(grade) for grade in grades.values()), reverse=True)[:k]
    best = dcg(ideal)
    if best == 0:
        return 0.0
    return dcg(gains) / best


def rate(part: int, whole: int) -> str:
    """Returns a share with its raw count beside it, as `55% (11/20)`.

    Every rate in a published table prints its count, because a percentage
    with no denominator hides how small the pool was.
    """
    return f"{share(part, whole)} ({part}/{whole})"


def report(
    rows: list[Row],
    grades: dict[str, int],
    queries: list[tuple[str, str]],
    reference_date: dt.date,
    today: dt.date,
    set_file: pathlib.PurePosixPath,
    per_query: int,
    shared: int,
    without_abstract: int,
) -> str:
    """Returns the whole measurement file as one string.

    `reference_date` is the date the graded set was built on, which fixes the
    Evidence window. `today` is the day this run happened. Both are printed,
    because the window moves on 1 January and a reader has to know which one
    produced the number.

    `set_file` is the path of the graded set inside the repository, and the
    link is built from it, so a moved set never leaves a dead link behind.

    `per_query`, `shared` and `without_abstract` are facts of this run. Every sentence below that
    names a number reads it from an argument, because a sentence written once
    by hand goes stale on the next run. See the two entries of that kind in
    `bugs.md`.
    """
    relevant = relevant_ids(grades)
    graded = len(grades)

    lines = [
        "# How well a ranking orders the Retrieval set",
        "",
        f"Measured on {today.isoformat()} by "
        "`uv run python -m fynd.cli measure-retrieval --as-of "
        f"{reference_date.isoformat()}`.",
        "",
        f"The pool is the {graded} Papers of "
        f"[{set_file.name}](../../{set_file}), each with a Relevance grade written "
        f"by hand. {len(relevant)} of them count as relevant, which is every Paper graded "
        "1 or 2. The set was built on "
        f"{reference_date.isoformat()}, and that date fixes the Evidence window of every "
        "search behind it.",
        "",
        f"Recall at {HEADLINE_CUT} is the headline, because {HEADLINE_CUT} is the cut a "
        "Project is built on. See "
        "[ADR 0013](../adr/0013-retrieval-ranks-in-python-over-a-pool-cut-to-20.md).",
        "",
        "The gain of a Paper in nDCG is its grade, so a 2 is worth twice a 1. That is the "
        "original linear form, and it is a stated default and not a choice made against "
        "these numbers.",
        "",
        f"The two kinds of number answer two questions. Recall at {SECOND_CUT} cannot pass "
        f"{SECOND_CUT} of {len(relevant)} Papers, which is "
        f"{share(SECOND_CUT, len(relevant))}, because there are only {SECOND_CUT} places. "
        f"So nDCG at {NDCG_CUT} says how well a row ordered the Papers it put in those "
        "places, and recall says how much of the pool it reached.",
        "",
        *(
            []
            if any(row.is_fynd_ranking for row in rows)
            else [
                "No row below is a ranking of Fynd. Every one of them is the order the "
                "search returned, which is the baseline the later rows are measured "
                "against.",
                "",
            ]
        ),
        *(
            [
                f"{without_abstract} Papers of the pool carry no abstract, so a row that "
                "reads text reads the title of those alone. That cuts both ways. A title "
                "is a short document, and BM25 divides a score by the length, so a title "
                "that holds a query word scores higher than a long abstract that holds "
                "it once. The abstracts are read from the search cache on the machine "
                "that runs this command, and they enter no file. See [ADR 0011]"
                "(../adr/0011-the-public-repository-holds-the-text-and-not-the-files.md).",
                "",
            ]
            if any(row.reads_text for row in rows)
            else []
        ),
        *(
            []
            if per_query >= HEADLINE_CUT
            else [
                f"A query row is not comparable with the baseline. One query returned "
                f"{per_query} Papers of the pool, so a query row cannot fill "
                f"{HEADLINE_CUT} places however good its order is, while the baseline "
                "chooses its places from the whole pool. The query rows compare with "
                "each other, and the spread between them is the finding.",
                "",
            ]
        ),
        "## The rows",
        "",
        "| Row | Recall at 20 | Recall at 10 | nDCG at 10 | What it ranks |",
        "|---|---|---|---|---|",
    ]

    for row in rows:
        at_20 = rate(*recall_at(row.ranking, grades, HEADLINE_CUT))
        at_10 = rate(*recall_at(row.ranking, grades, SECOND_CUT))
        score = ndcg_at(row.ranking, grades, NDCG_CUT)
        lines.append(f"| {row.name} | {at_20} | {at_10} | {score:.3f} | {row.note} |")

    lines += [
        "",
        "## The queries",
        "",
        f"The pool was built by {len(queries)} queries, {per_query} Papers from each. "
        + (
            "They share no Paper at all, so a query row reaches only the Papers of its own query."
            if shared == 0
            else f"{shared} Papers were returned by more than one query."
        ),
        "",
        "| Query | Text |",
        "|---|---|",
    ]
    for name, text in queries:
        lines.append(f"| {name} | `{text}` |")

    lines += [
        "",
        "## The limits",
        "",
        "One person wrote every published grade, because Fynd is the project of one "
        "student. There is no agreement number between two people, and no published "
        "number here is scored against a model pass.",
        "",
        "Recall over a pool is recall inside the pool. A relevant Paper that none of the "
        "four queries returned is invisible to every number above, and a Paper in a row "
        "that nobody graded counts as nothing.",
        "",
        "No number says whether Fynd finds United Kingdom evidence, because the grading "
        "rule ignores the country by design.",
        "",
        "Every constant sits at its published default and no constant was tuned. Tuning "
        f"against the same {graded} Papers this table reports would fit the set.",
        "",
    ]
    return "\n".join(lines)

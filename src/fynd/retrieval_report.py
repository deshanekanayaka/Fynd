"""Calculates ranking metrics and formats the Retrieval set comparison table.

The CLI supplies Paper orders, human Relevance grades, and run metadata.
Metric functions score those orders; row builders prepare baseline and dense
comparisons. Dense rows use a supplied embedding function, which may call a
service. This file returns Markdown; the CLI saves it under docs/measurements.
"""

import datetime as dt
import math
import pathlib
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Final

from fynd.measure import share
from fynd.models import Paper, SearchResult
from fynd.retrieval import Embed, dense_ranking
from fynd.retrieval_set import entries_from

# Count both partly relevant and fully relevant Papers in recall.
RELEVANT_GRADES: Final = (1, 2)

# Measure coverage at the planned 20-Paper cut and ordering within the first 10.
HEADLINE_CUT: Final = 20
SECOND_CUT: Final = 10
NDCG_CUT: Final = 10

# Compare 1024 and 512 dimensions to measure the effect of reducing vector size.
DENSE_SIZES: Final = (1024, 512)


# Use linear gain, so grade 2 is worth twice grade 1; keep that measurement choice explicit.
def gain_of(grade: int) -> int:
    """Returns a Paper’s Relevance grade as its nDCG gain."""
    return grade


@dataclass(frozen=True)
class Row:
    """One comparison row with its ordered identifiers and configuration notes."""

    name: str
    note: str
    # Keep short query rows as-is; padding would invent returned Papers.
    ranking: list[str] = field(default_factory=list)
    # Distinguish Fynd's computed orders from the service's original search order.
    is_fynd_ranking: bool = False
    # Controls whether the report includes its missing-abstract explanation.
    reads_text: bool = False


def rows_from_searches(
    results: list[tuple[str, SearchResult]], per_query: int, pool_size: int
) -> list[Row]:
    """Builds the interleaved baseline and individual query rows from search replies."""
    # Reuse the set builder's pooling order without consulting human grades.
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


def dense_rows(
    asked: list[tuple[str, str]],
    papers: list[Paper],
    embed_at: Callable[[int], Embed],
    model: str,
    sizes: tuple[int, ...] = DENSE_SIZES,
) -> list[Row]:
    """Builds a dense ranking row for each requested vector size and search string."""
    # Keep label and subject-query comparisons visible, not just the better result.
    rows = []
    for size in sizes:
        embed = embed_at(size)
        for what, text in asked:
            rows.append(
                Row(
                    name=f"Meaning {size}, {what}",
                    note=(
                        f"The meaning ranking of `{model}` at {size} values, "
                        f"asked for the {what} `{text}`"
                    ),
                    ranking=[item.paper_id for item in dense_ranking(text, papers, embed)],
                    is_fynd_ranking=True,
                    reads_text=True,
                )
            )
    return rows


def shared_papers(results: list[tuple[str, SearchResult]], per_query: int) -> int:
    """Counts eligible Paper identifiers appearing more than once across search results."""
    seen: dict[str, int] = {}
    for _, result in results:
        for paper in result.papers[:per_query]:
            seen[paper.paper_id] = seen.get(paper.paper_id, 0) + 1
    return sum(1 for count in seen.values() if count > 1)


def relevant_ids(grades: dict[str, int]) -> set[str]:
    """Returns identifiers whose Relevance grade is 1 or 2."""
    return {paper_id for paper_id, grade in grades.items() if grade in RELEVANT_GRADES}


def recall_at(ranking: list[str], grades: dict[str, int], k: int) -> tuple[int, int]:
    """Counts relevant Papers in the first k positions against all relevant pool Papers."""
    relevant = relevant_ids(grades)
    # The denominator is the full relevant pool, even when this ranking is short.
    found = sum(1 for paper_id in ranking[:k] if paper_id in relevant)
    return found, len(relevant)


def dcg(gains: list[int]) -> float:
    """Sums gains with lower weight for later ranking positions."""
    # A grade in second place is divided by log2(3); earlier results count more.
    return sum(gain / math.log2(place + 1) for place, gain in enumerate(gains, start=1))


def ndcg_at(ranking: list[str], grades: dict[str, int], k: int) -> float:
    """Compares top-k gains with the best possible top-k gains in the graded pool."""
    # Unknown identifiers receive zero gain without shifting the later positions.
    gains = [gain_of(grades.get(paper_id, 0)) for paper_id in ranking[:k]]
    ideal = sorted((gain_of(grade) for grade in grades.values()), reverse=True)[:k]
    best = dcg(ideal)
    if best == 0:
        return 0.0
    return dcg(gains) / best


def rate(part: int, whole: int) -> str:
    """Formats a percentage with its numerator and denominator."""
    # Raw counts keep a percentage's pool size visible.
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
    """Formats ranking metrics, configuration notes, and limitations as Markdown."""
    relevant = relevant_ids(grades)
    graded = len(grades)
    # A top-10 list cannot recover more relevant Papers than the pool contains.
    reachable_at_10 = min(SECOND_CUT, len(relevant))

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
        f"{reachable_at_10} of {len(relevant)} Papers, which is "
        f"{share(reachable_at_10, len(relevant))}, because there are only {SECOND_CUT} places. "
        f"So nDCG at {NDCG_CUT} says how well a row ordered the Papers it put in those "
        "places, and recall says how much of the pool it reached.",
        "",
    ]
    if not any(row.is_fynd_ranking for row in rows):
        lines += [
            "No row below is a ranking of Fynd. Every one of them is the order the "
            "search returned, which is the baseline the later rows are measured "
            "against.",
            "",
        ]
    if any(row.reads_text for row in rows):
        lines += [
            f"{without_abstract} Papers of the pool carry no abstract, so a row that "
            "reads text reads the title of those alone. That cuts both ways. A title "
            "is a short document, and BM25 divides a score by the length, so a title "
            "that holds a query word scores higher than a long abstract that holds "
            "it once. The abstracts are read from the search cache on the machine "
            "that runs this command, and they enter no file. See [ADR 0011]"
            "(../adr/0011-the-public-repository-holds-the-text-and-not-the-files.md).",
            "",
        ]
    if per_query < HEADLINE_CUT:
        lines += [
            f"A query row is not comparable with the baseline. One query returned "
            f"{per_query} Papers of the pool, so a query row cannot fill "
            f"{HEADLINE_CUT} places however good its order is, while the baseline "
            "chooses its places from the whole pool. The query rows compare with "
            "each other, and the spread between them is the finding.",
            "",
        ]
    lines += [
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

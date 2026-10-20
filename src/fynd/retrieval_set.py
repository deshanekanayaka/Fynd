"""Build the Retrieval set, which is the Papers a retrieval number is scored on.

The set is 40 to 60 Papers of the Seeded Topic, each with a Relevance grade a
person writes by hand. One query returns too few Papers to grade, so four
queries build it, and the set records which ones returned each Paper.

Two rules matter more than the rest. The file ships shuffled, because a grade
read in rank order is not a grade, it is agreement with the ranking. And the
file holds no abstract, because ADR 0011 refuses a committed abstract and this
file enters git.

Nothing here reads a clock. The caller passes the reference date, as stage 2
does, so the Evidence window of a published number never moves on 1 January.
"""

import datetime as dt
import random
from typing import Final, Literal, Protocol

from pydantic import BaseModel, Field

from fynd.models import SearchResult
from fynd.stages.stage2 import SEEDED_TOPIC, first_year_in_window

# What each query asks the search for. 50 is the limit the shipped flow uses,
# so the cache this run fills is the cache a shipped run reads. See ADR 0013.
SEARCH_LIMIT: Final = 50

# The most Papers one query may contribute. Four queries at 20 give at most 80
# before the duplicates go, so the pool is also capped at SET_MAX below. The
# other 30 Papers of each reply stay in the cache for a later run to read.
PER_QUERY: Final = 20

# The set is useless outside this band. Too few Papers and recall at 20 is
# arithmetic on nothing. Too many and the grading never finishes.
SET_MIN: Final = 40
SET_MAX: Final = 60

# A fixed seed, so a re-run writes the same order and a later re-grade reads
# the same file. The date it was chosen on carries no meaning beyond that.
SHUFFLE_SEED: Final = 20261020


class SetTooSmall(Exception):
    """Raised when the four queries pooled too few Papers to grade.

    There is no matching error for too many. The pool stops at SET_MAX while it
    is built, so only the lower end can fail.
    """


class SeedQuery(BaseModel):
    """One of the four queries that build the set."""

    # The name is what an entry records, because a reader of the file should
    # not have to match a long query string to know where a Paper came from.
    name: str
    text: str
    # Who wrote the text, which is `model` or `hand`. CONTEXT.md fixes the word
    # Source for anything Fynd cites, so this field does not use it. The model
    # one is the finding this set exists to measure, so it is named in the file.
    written_by: str
    note: str


class SetEntry(BaseModel):
    """One Paper of the Retrieval set, waiting for its grade."""

    paper_id: str
    title: str
    # No year. The grading rule says to read the title and the abstract and
    # nothing else, and the Evidence window already keeps every Paper in the
    # set inside the last 5 years, so a year on the line separates nothing and
    # can push a grade down for a reason the rule does not allow.
    # A Relevance grade is 0, 1 or 2, and None means nobody has graded it yet.
    # The type refuses a fourth value, because a typo in a hand edited file
    # would otherwise reach the recall arithmetic.
    grade: Literal[0, 1, 2] | None = None
    queries: list[str] = Field(default_factory=list)


class RetrievalSet(BaseModel):
    """The whole set, as the file on disk holds it."""

    topic: str
    reference_date: dt.date
    search_limit: int
    per_query: int
    # How many Papers the four queries offered, before the cap. When this is
    # larger than the number of entries, the cap left Papers out, and a reader
    # of a recall number has to know that the pool was truncated.
    papers_offered: int
    shuffle_seed: int
    queries: list[SeedQuery]
    entries: list[SetEntry]


class Search(Protocol):
    """The search this file needs, passed in as a plain function argument."""

    def __call__(self, query: str, year_from: int, limit: int) -> SearchResult: ...


# The three queries written by hand. The fourth is the one the model wrote, and
# it arrives as an argument, because no placeholder in this file would be the
# thing the model actually said.
HAND_QUERIES: Final = (
    SeedQuery(
        name="hand",
        text=SEEDED_TOPIC,
        written_by="hand",
        note="The Seeded Topic written out, which is the query the measured runs used.",
    ),
    SeedQuery(
        name="wider",
        text="household energy demand forecasting",
        written_by="hand",
        note="The same subject with the country dropped, which should return more Papers.",
    ),
    SeedQuery(
        name="narrower",
        text="United Kingdom smart meter load forecasting",
        written_by="hand",
        note="One step narrower, which should return fewer Papers and more exact ones.",
    ),
)


def entries_from(
    results: list[tuple[str, SearchResult]],
    per_query: int,
    cap: int = SET_MAX,
) -> list[SetEntry]:
    """Pools the Papers of every query into one list of entries.

    A Paper two queries both returned is one entry that names both, because the
    set is a pool of Papers and not a pool of results.

    The queries take turns, one rank at a time, and the pool stops at the cap.
    Reading each query to the end instead would spend the whole budget on the
    first query and leave the fourth unrepresented. Every query that returned a
    Paper is still recorded on that Paper, whichever turn placed it.
    """
    by_identifier: dict[str, SetEntry] = {}
    # Only the first Papers of a reply are eligible. The search asked for more
    # so the shipped limit is exercised and the cache is filled.
    eligible = [(name, result.papers[:per_query]) for name, result in results]

    for rank in range(per_query):
        for name, papers in eligible:
            if rank >= len(papers):
                continue
            paper = papers[rank]
            entry = by_identifier.get(paper.paper_id)
            if entry is not None:
                if name not in entry.queries:
                    entry.queries.append(name)
                continue
            if len(by_identifier) >= cap:
                # The pool is full. The loop runs on, because a Paper already
                # in the pool still has to record the query that found it.
                continue
            # The abstract is read from the cache at measurement time and is
            # deliberately absent here. See ADR 0011.
            by_identifier[paper.paper_id] = SetEntry(
                paper_id=paper.paper_id,
                title=paper.title,
                queries=[name],
            )
    return list(by_identifier.values())


def papers_offered(results: list[tuple[str, SearchResult]], per_query: int) -> int:
    """Counts the Papers the queries offered, before the cap took its share."""
    identifiers = set()
    for _, result in results:
        for paper in result.papers[:per_query]:
            identifiers.add(paper.paper_id)
    return len(identifiers)


def shuffled(entries: list[SetEntry], seed: int) -> list[SetEntry]:
    """Returns the entries in a fixed random order, leaving the input alone.

    The rank order has to go. A person grading a list top to bottom agrees with
    the ranking instead of judging the Paper, and this set exists to disagree
    with the ranking when the ranking is wrong.
    """
    mixed = list(entries)
    random.Random(seed).shuffle(mixed)
    return mixed


def build_set(
    search: Search,
    reference_date: dt.date,
    model_query: str,
) -> RetrievalSet:
    """Runs the four queries and returns the set, shuffled and ungraded."""
    queries = [
        SeedQuery(
            name="model",
            text=model_query,
            written_by="model",
            note=(
                "The query the model wrote for the Seeded Topic, recorded exactly as it "
                "arrived and before any shape check existed. See issue 38."
            ),
        ),
        *HAND_QUERIES,
    ]

    year_from = first_year_in_window(reference_date)
    results = []
    for query in queries:
        results.append((query.name, search(query.text, year_from=year_from, limit=SEARCH_LIMIT)))

    offered = papers_offered(results, per_query=PER_QUERY)
    entries = entries_from(results, per_query=PER_QUERY, cap=SET_MAX)
    if len(entries) < SET_MIN:
        raise SetTooSmall(
            f"The four queries pooled {len(entries)} Papers, and the set needs "
            f"{SET_MIN} to {SET_MAX}. The queries overlap too much, so widen one of them."
        )

    return RetrievalSet(
        topic=SEEDED_TOPIC,
        reference_date=reference_date,
        search_limit=SEARCH_LIMIT,
        per_query=PER_QUERY,
        papers_offered=offered,
        shuffle_seed=SHUFFLE_SEED,
        queries=queries,
        entries=shuffled(entries, SHUFFLE_SEED),
    )

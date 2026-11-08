"""Builds the Paper pool used for human grading and ranking measurements.

The CLI supplies a search function and reference date. Four handwritten
queries contribute Papers for the Seeded Topic; duplicates are merged and
the 40–60 entries are shuffled for grading. Saved entries omit abstracts;
the caller later supplies search replies containing that text (ADR 0011)."""

import datetime as dt
import random
from typing import Final, Literal, Protocol

from pydantic import BaseModel, Field

from fynd.models import Paper, SearchResult
from fynd.stages.stage2 import SEEDED_TOPIC, SEEDED_TOPIC_QUERY, first_year_in_window

# Request 50 per query to match the intended retrieval search size (ADR 0013).
SEARCH_LIMIT: Final = 50

# Taking 15 from each of 4 queries keeps their combined pool within the 60-Paper cap.
PER_QUERY: Final = 15

# Keep enough Papers to compare rankings without making hand grading too large.
SET_MIN: Final = 40
SET_MAX: Final = 60

# The same input order and seed reproduce the same shuffle.
SHUFFLE_SEED: Final = 20261020


class SetTooSmall(Exception):
    """Raised when the query pool contains fewer than 40 distinct Papers."""


class SeedQuery(BaseModel):
    """One search phrasing with its name, author type, and purpose."""

    # Entries record this short name so overlapping query results are easy to trace.
    name: str
    text: str
    # All four current queries are handwritten; this records their provenance.
    written_by: str
    note: str


class SetEntry(BaseModel):
    """One Retrieval set Paper with its query names and optional Relevance grade."""

    paper_id: str
    title: str
    # None means ungraded; restrict saved values so a typo cannot corrupt the metrics.
    grade: Literal[0, 1, 2] | None = None
    queries: list[str] = Field(default_factory=list)


class RetrievalSet(BaseModel):
    """A saved Paper pool with its Topic, queries, date, and build settings."""

    topic: str
    # Keep old files loadable; measurement refuses an empty subject query (ADR 0015).
    topic_query: str = ""
    reference_date: dt.date
    search_limit: int
    per_query: int
    # Count distinct eligible Papers before the overall cap to expose truncation.
    papers_offered: int
    shuffle_seed: int
    queries: list[SeedQuery]
    entries: list[SetEntry]


class Search(Protocol):
    """A supplied search function accepting query text, first year, and result limit."""

    def __call__(self, query: str, year_from: int, limit: int) -> SearchResult: ...


# Use one Topic so every Paper’s grade answers the same relevance question.
# Handwritten queries measure ranking, not the quality of AI-generated queries.
SEED_QUERIES: Final = (
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
    SeedQuery(
        name="reworded",
        text="domestic electricity consumption prediction United Kingdom",
        written_by="hand",
        note="The same Topic in other words, which tests the ranking on vocabulary.",
    ),
)


def entries_from(
    results: list[tuple[str, SearchResult]],
    per_query: int,
    cap: int = SET_MAX,
) -> list[SetEntry]:
    """Pools eligible Papers by alternating queries and merging repeated identifiers."""
    by_identifier: dict[str, SetEntry] = {}
    # Only each query’s first per_query results may enter this evaluation pool.
    eligible = [(name, result.papers[:per_query]) for name, result in results]

    # Alternate queries so a cap cannot favour only the first query.
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
                # Keep scanning so later matches can still add query names to retained Papers.
                continue
            # Public entries omit abstracts (ADR 0011) and years that grading must ignore.
            by_identifier[paper.paper_id] = SetEntry(
                paper_id=paper.paper_id,
                title=paper.title,
                queries=[name],
            )
    return list(by_identifier.values())


def pool_papers(
    results: list[tuple[str, SearchResult]], per_query: int, keep: set[str]
) -> list[Paper]:
    """Returns retained Papers with abstracts from the supplied search replies."""
    # Exclude ungraded results so ranking and evaluation describe the same pool.
    found: dict[str, Paper] = {}
    for _, result in results:
        for paper in result.papers[:per_query]:
            if paper.paper_id in keep and paper.paper_id not in found:
                found[paper.paper_id] = paper
    return list(found.values())


def papers_without_abstract(papers: list[Paper]) -> int:
    """Counts Papers whose abstract is empty."""
    return sum(1 for paper in papers if not paper.abstract)


def papers_offered(results: list[tuple[str, SearchResult]], per_query: int) -> int:
    """Counts distinct eligible Papers before the overall pool cap."""
    identifiers = set()
    for _, result in results:
        for paper in result.papers[:per_query]:
            identifiers.add(paper.paper_id)
    return len(identifiers)


def shuffled(entries: list[SetEntry], seed: int) -> list[SetEntry]:
    """Returns a reproducibly shuffled copy of the entry list."""
    # Hide ranking-order cues without changing the original list order.
    mixed = list(entries)
    random.Random(seed).shuffle(mixed)
    return mixed


def build_set(search: Search, reference_date: dt.date) -> RetrievalSet:
    """Builds a shuffled, ungraded Retrieval set using a fixed reference date."""
    queries = list(SEED_QUERIES)

    # The passed date keeps the Evidence window stable during replay.
    year_from = first_year_in_window(reference_date)
    results = []
    for query in queries:
        results.append((query.name, search(query.text, year_from=year_from, limit=SEARCH_LIMIT)))

    offered = papers_offered(results, per_query=PER_QUERY)
    entries = entries_from(results, per_query=PER_QUERY, cap=SET_MAX)
    if len(entries) < SET_MIN:
        raise SetTooSmall(
            f"The four queries pooled {len(entries)} Papers, and the set needs "
            f"{SET_MIN} to {SET_MAX}. Results may be sparse or overlapping; review the query texts."
        )

    return RetrievalSet(
        topic=SEEDED_TOPIC,
        topic_query=SEEDED_TOPIC_QUERY,
        reference_date=reference_date,
        search_limit=SEARCH_LIMIT,
        per_query=PER_QUERY,
        papers_offered=offered,
        shuffle_seed=SHUFFLE_SEED,
        queries=queries,
        entries=shuffled(entries, SHUFFLE_SEED),
    )

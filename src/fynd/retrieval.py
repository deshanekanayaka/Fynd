"""Ranks Papers by words and by meaning.

ADR 0013 keeps ranking in Python and passes the top 20 Papers onward.
The caller supplies the embedding function so tests need no network.
"""

import math
import re
from dataclasses import dataclass, replace
from typing import Final, Protocol

from fynd.models import Paper

# Keep standard defaults so these settings are not fitted to the Retrieval set.
BM25_K1: Final = 1.2
BM25_B: Final = 0.75

# Top 20 continue (ADR 0013).
CUT: Final = 20

WORD = re.compile(r"\w+")

# Temporary rules pending a measured library replacement.
ENDINGS: Final = ("ing", "es", "ed", "s")

MIN_STEM: Final = 4

NOT_A_PLURAL_AFTER: Final = ("s", "i", "u")


@dataclass(frozen=True)
class Ranked:
    """One Paper with its ranking score and match reasons."""

    paper_id: str  # Semantic Scholar’s identifier.
    score: float  # Ranking value, not a probability.
    terms: tuple[str, ...] = ()
    meaning_is_close: bool = False  # In the dense ranking’s top cut.


class Embed(Protocol):
    """An embedding function that returns one vector per input text."""

    def __call__(self, texts: list[str], input_type: str) -> list[list[float]]: ...


def stem(word: str) -> str:
    """Removes one recognised word ending."""
    for ending in ENDINGS:
        # A minimum length keeps short words such as "gas" intact.
        if not word.endswith(ending) or len(word) - len(ending) < MIN_STEM:
            continue
        # The final "s" in words such as "process" is not a plural ending.
        if ending == "s" and word[-2] in NOT_A_PLURAL_AFTER:
            continue
        return word[: -len(ending)]
    return word


def tokens(text: str) -> list[str]:
    """Lowercases, splits, and stems text."""
    return [stem(word) for word in WORD.findall(text.lower())]


def document_text(paper: Paper) -> str:
    """Joins a Paper's title and abstract for ranking."""
    return f"{paper.title} {paper.abstract}".strip()


def matched_terms(query: str, text: str) -> tuple[str, ...]:
    """Returns matching query stems once each, in query order."""
    held = set(tokens(text))
    found: list[str] = []
    for word in tokens(query):
        if word in held and word not in found:
            found.append(word)
    return tuple(found)


def ordered(
    scores: dict[str, float],
    terms: dict[str, tuple[str, ...]] | None = None,
) -> list[Ranked]:
    """Sorts Papers by descending score and identifier on ties."""
    # Higher scores mean stronger matches, so the top cut keeps them first.
    # Identifier ties make repeated measurements independent of input order.
    places = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [
        Ranked(
            paper_id=paper_id,
            score=score,
            terms=(terms or {}).get(paper_id, ()),
        )
        for paper_id, score in places
    ]


def bm25_ranking(query: str, papers: list[Paper]) -> list[Ranked]:
    """Ranks Papers by keyword relevance."""
    if not papers:
        return []

    documents = {paper.paper_id: tokens(document_text(paper)) for paper in papers}
    lengths = [len(words) for words in documents.values()]
    average_length = sum(lengths) / len(lengths)

    holders: dict[str, int] = {}
    for words in documents.values():
        for word in set(words):
            holders[word] = holders.get(word, 0) + 1

    total = len(documents)
    scores: dict[str, float] = {}
    terms: dict[str, tuple[str, ...]] = {}
    for paper_id, words in documents.items():
        length = len(words)
        score = 0.0
        matched: list[str] = []
        for word in tokens(query):
            held_by = holders.get(word, 0)
            if held_by == 0:
                continue
            frequency = words.count(word)
            if frequency == 0:
                continue
            if word not in matched:
                matched.append(word)

            # A word found in fewer Papers is more useful for distinguishing them.
            idf = math.log(1 + (total - held_by + 0.5) / (held_by + 0.5))

            # Adjust for length so longer abstracts do not win by having more words.
            weight = BM25_K1 * (1 - BM25_B + BM25_B * length / average_length)
            # Repeated matches help, but each extra occurrence adds less credit.
            score += idf * frequency * (BM25_K1 + 1) / (frequency + weight)
        scores[paper_id] = score
        terms[paper_id] = tuple(matched)
    return ordered(scores, terms=terms)


def cosine(left: list[float], right: list[float]) -> float:
    """Measures similarity between two vectors."""
    if len(left) != len(right):
        # Mixing vector sizes would produce a misleading similarity score.
        raise ValueError(
            f"A vector of {len(left)} values cannot be compared with one of {len(right)}. "
            "Both the query and the documents must be embedded at the same size."
        )
    size = math.sqrt(sum(value * value for value in left)) * math.sqrt(
        sum(value * value for value in right)
    )
    if size == 0:
        # A zero vector has no direction; returning zero avoids division by zero.
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / size


def dense_ranking(query: str, papers: list[Paper], embed: Embed, cut: int = CUT) -> list[Ranked]:
    """Ranks Papers by embedding similarity."""
    if not papers:
        return []

    # Queries and documents use different embedding modes.
    query_vector = embed([query], input_type="query")[0]
    documents = [document_text(paper) for paper in papers]
    vectors = embed(documents, input_type="document")
    if len(vectors) != len(documents):
        # A short reply would silently drop Papers when paired with zip.
        raise ValueError(
            f"The embedding call returned {len(vectors)} vectors for {len(documents)} "
            "Papers, so the pool and the vectors do not describe the same Papers."
        )

    scores = {
        paper.paper_id: cosine(query_vector, vector) for paper, vector in zip(papers, vectors)
    }
    by_meaning = ordered(scores)
    # The flag marks the top cut; it is not a universal similarity threshold.
    return [replace(item, meaning_is_close=place < cut) for place, item in enumerate(by_meaning)]

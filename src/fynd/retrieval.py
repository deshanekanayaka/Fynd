"""Rank a pool of Papers, so the cut to 20 keeps the right ones.

The search asks for 50 Papers and a Project is built on 20, so this file
decides which 20. It holds the four rankings the measured table compares: the
keyword ranking, the meaning ranking, the fusion of the two, and the fusion
reordered by a hosted reranker. See ADR 0013.

Nothing here reaches the network and nothing here reads a clock. The embedding
function and the reranker arrive as plain function arguments, so the same code
serves a Stage and a test. The measured number therefore comes from the code
that runs for a student.

Every constant below is the published default of the method it belongs to, and
nothing is tuned. Tuning a constant against the 60 Papers the table reports
would fit the set and publish a number that means nothing.
"""

import math
import re
from dataclasses import dataclass
from typing import Final, Protocol

from fynd.models import Paper

# The published defaults of BM25. k1 controls how much a repeated word still
# counts, and b controls how much a long abstract is penalised.
BM25_K1: Final = 1.2
BM25_B: Final = 0.75

# The published default of reciprocal rank fusion. A large k flattens the gap
# between rank 1 and rank 2, so one ranking cannot win on its own.
RRF_K: Final = 60

# How many Papers the ranking passes on. ADR 0013 fixes this at 20, because the
# Open copy pipeline and stage 3 read every Paper that gets through.
CUT: Final = 20

# A word splits on anything that is not a letter or a digit. A digit stays,
# because a year or a figure in a title is a word a query can match. The class
# covers every alphabet and not only the English one, because a title holds an
# author name and a place name, and "Müller" split on the letter u would leave
# two fragments that match nothing and still count towards the length.
WORD = re.compile(r"\w+")

# The endings a word loses before it is matched. So "households" matches
# "household" and "forecasting" matches "forecast", which is what a reader
# means by the same word. The longest ending is tried first, or "forecasting"
# would lose only its "g".
# ponytail: a short rule and not a stemmer. It leaves "electricity" and
# "electric" apart, it stems "modelling" to "modell" while "model" stays
# "model", and it leaves "analysis" and "analyses" apart. Add a Porter stemmer
# if the BM25 row of the table reads low.
ENDINGS: Final = ("ing", "es", "ed", "s")

# What has to be left after an ending comes off. Without a floor, "gas" becomes
# "ga" and "uses" becomes "us", which are not words and match the wrong Papers.
MIN_STEM: Final = 4

# A final "s" after one of these letters is part of the word and not a plural.
# Without this, "process" becomes "proces" while "processing" becomes
# "process", so the two stop matching, which is the opposite of the point.
NOT_A_PLURAL_AFTER: Final = ("s", "i", "u")


@dataclass(frozen=True)
class Ranked:
    """One Paper in a ranking, with the score that placed it there."""

    paper_id: str
    score: float


class Embed(Protocol):
    """The embedding call this file needs, passed in as a function argument.

    `input_type` is "query" or "document". Voyage embeds the two differently,
    and sending a query as a document measures the wrong distance.
    """

    def __call__(self, texts: list[str], input_type: str) -> list[list[float]]: ...


class Rerank(Protocol):
    """The reranker call this file needs. It answers with (index, score) pairs.

    The index is a place in the documents list the caller sent, because a
    hosted reranker returns its own order and not the order it was given.
    """

    def __call__(self, query: str, documents: list[str]) -> list[tuple[int, float]]: ...


def stem(word: str) -> str:
    """Returns the word with one grammatical ending removed."""
    for ending in ENDINGS:
        if not word.endswith(ending) or len(word) - len(ending) < MIN_STEM:
            continue
        if ending == "s" and word[-2] in NOT_A_PLURAL_AFTER:
            continue
        return word[: -len(ending)]
    return word


def tokens(text: str) -> list[str]:
    """Returns the words of this text, lowercased and stemmed."""
    return [stem(word) for word in WORD.findall(text.lower())]


def document_text(paper: Paper) -> str:
    """Returns the text a ranking reads for one Paper, which is title and abstract.

    A Paper with no abstract is ranked on its title alone. 8 of the 60 Papers
    of the Retrieval set have no abstract, and dropping them would change the
    pool a recall number is measured over.
    """
    return f"{paper.title} {paper.abstract}".strip()


def ordered(scores: dict[str, float]) -> list[Ranked]:
    """Returns the Papers from the best score down, and by identifier on a tie.

    The identifier decides a tie on purpose. Two Papers with the same score
    would otherwise sit in whatever order the pool arrived in, and a published
    number has to repeat exactly on a second run.
    """
    places = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [Ranked(paper_id=paper_id, score=score) for paper_id, score in places]


def bm25_ranking(query: str, papers: list[Paper]) -> list[Ranked]:
    """Ranks the pool by keyword match, with BM25 at its published defaults.

    Every Paper of the pool comes back, including the ones that match no word
    at all. The cut takes the first 20, so a ranking that dropped the Papers
    with no match would hide them from a recall number instead of ranking
    them last.
    """
    if not papers:
        return []

    documents = {paper.paper_id: tokens(document_text(paper)) for paper in papers}
    lengths = [len(words) for words in documents.values()]
    average_length = sum(lengths) / len(lengths)

    # How many documents hold each word. One pass, because the pool is tens of
    # Papers and this runs once per query.
    holders: dict[str, int] = {}
    for words in documents.values():
        for word in set(words):
            holders[word] = holders.get(word, 0) + 1

    total = len(documents)
    scores: dict[str, float] = {}
    for paper_id, words in documents.items():
        length = len(words)
        score = 0.0
        for word in tokens(query):
            held_by = holders.get(word, 0)
            if held_by == 0:
                continue
            frequency = words.count(word)
            if frequency == 0:
                continue
            # The Lucene form of the inverse document frequency. The 1 inside
            # the logarithm keeps it positive, so a word in every document
            # adds nothing instead of subtracting.
            idf = math.log(1 + (total - held_by + 0.5) / (held_by + 0.5))
            # A long document needs more matches to score the same, because a
            # word in a 300 word abstract says less than one in a title.
            weight = BM25_K1 * (1 - BM25_B + BM25_B * length / average_length)
            score += idf * frequency * (BM25_K1 + 1) / (frequency + weight)
        scores[paper_id] = score
    return ordered(scores)


def cosine(left: list[float], right: list[float]) -> float:
    """Returns the cosine similarity of two vectors, and 0.0 for a zero vector.

    Raises ValueError when the two vectors are not the same size.
    """
    if len(left) != len(right):
        # The table reports this model at 1024 and at 512, so one run can hold
        # both sizes. Comparing across the two gives a number that looks like a
        # similarity and is not one, which would quietly deflate a whole row.
        raise ValueError(
            f"A vector of {len(left)} values cannot be compared with one of {len(right)}. "
            "Both the query and the documents must be embedded at the same size."
        )
    size = math.sqrt(sum(value * value for value in left)) * math.sqrt(
        sum(value * value for value in right)
    )
    if size == 0:
        # A vendor that answers with zeros would otherwise divide by zero and
        # lose the whole ranking. Such a Paper ranks last instead.
        return 0.0
    return sum(a * b for a, b in zip(left, right)) / size


def dense_ranking(query: str, papers: list[Paper], embed: Embed) -> list[Ranked]:
    """Ranks the pool by meaning, with one embedding call for the whole pool.

    The query and the documents are two calls, because a vendor embeds a query
    and a document differently.
    """
    if not papers:
        return []

    query_vector = embed([query], input_type="query")[0]
    documents = [document_text(paper) for paper in papers]
    vectors = embed(documents, input_type="document")
    if len(vectors) != len(documents):
        # Zipping a short answer would drop the last Papers of the pool, and a
        # recall number would then be measured over fewer Papers than were
        # graded, with nothing on screen to say so.
        raise ValueError(
            f"The embedding call returned {len(vectors)} vectors for {len(documents)} "
            "Papers, so the pool and the vectors do not describe the same Papers."
        )

    scores = {
        paper.paper_id: cosine(query_vector, vector) for paper, vector in zip(papers, vectors)
    }
    return ordered(scores)


def fuse(rankings: list[list[Ranked]], k: int = RRF_K) -> list[Ranked]:
    """Merges several rankings with reciprocal rank fusion.

    Fusion reads the place of a Paper and never its score, which is why it can
    merge a BM25 score and a cosine similarity at all. The two are numbers on
    different scales, and adding them would let whichever runs larger decide
    every order.
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for place, item in enumerate(ranking, start=1):
            scores[item.paper_id] = scores.get(item.paper_id, 0.0) + 1 / (k + place)
    return ordered(scores)


def rerank_ranking(query: str, papers: list[Paper], rerank: Rerank) -> list[Ranked]:
    """Reorders the Papers it is given with a hosted reranker.

    The caller passes the pool in the order the fusion left it, and decides how
    deep to go. A reranker reads the query and one document together, so it
    costs one call over the whole list and it cannot run on a cut of one Paper.
    """
    if not papers:
        return []

    documents = [document_text(paper) for paper in papers]
    answer = rerank(query, documents)

    # A reranker that answered about fewer Papers than it was sent leaves the
    # rest at a score of 0.0, which ranks them last. Dropping them would
    # shorten the pool a recall number is measured over.
    scores = {paper.paper_id: 0.0 for paper in papers}
    for index, score in answer:
        # The index arrives from outside Fynd. A number past the end of the
        # pool would raise in the middle of a run, and a negative one would
        # count backwards from the end and score the wrong Paper in silence.
        if not 0 <= index < len(papers):
            raise ValueError(
                f"The reranker scored document {index} of a list of {len(papers)}. "
                "The reply does not describe the pool it was sent."
            )
        scores[papers[index].paper_id] = score
    # Through `ordered`, so two equal scores break the tie by identifier. The
    # vendor's own order is not repeatable, and a published number has to be.
    return ordered(scores)

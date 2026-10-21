"""Rank a pool of Papers, so the cut to 20 keeps the right ones.

The search asks for 50 Papers and a Project is built on 20, so this file
decides which 20. It holds the four rankings the measured table will compare: the
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
from dataclasses import dataclass, replace
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
    """One Paper in a ranking, with the score and the reason that placed it there.

    The two reason fields are the facts the stage 4 card prints. A term match
    names its stems. A meaning match says the meaning is close with no exact
    term match. No model writes that line, and nothing here writes a sentence.
    See ADR 0014.
    """

    paper_id: str
    score: float
    # The stems of the query this Paper holds, in the order the query wrote
    # them. Empty means the Paper matched no word of the query, which the card
    # says as plainly as a match.
    terms: tuple[str, ...] = ()
    # Whether the meaning ranking placed this Paper inside the cut. A Paper
    # with no terms and a close meaning is the one case a student has to be
    # told about, because nothing on the card would otherwise explain it.
    meaning_is_close: bool = False


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

    A Paper with no abstract is ranked on its title alone, and the measured
    table counts how many of those a pool holds. Dropping them instead would
    change the pool a recall number is measured over.
    """
    return f"{paper.title} {paper.abstract}".strip()


def matched_terms(query: str, text: str) -> tuple[str, ...]:
    """Returns the stems of the query that this text holds, in the query order.

    The query order and not the alphabet, because the card prints these words
    and a student reads them against the query they just saw. A stem appears
    once however many times the text repeats it.
    """
    held = set(tokens(text))
    found: list[str] = []
    for word in tokens(query):
        if word in held and word not in found:
            found.append(word)
    return tuple(found)


def ordered(
    scores: dict[str, float],
    terms: dict[str, tuple[str, ...]] | None = None,
    close: set[str] | None = None,
) -> list[Ranked]:
    """Returns the Papers from the best score down, and by identifier on a tie.

    The identifier decides a tie on purpose. Two Papers with the same score
    would otherwise sit in whatever order the pool arrived in, and a published
    number has to repeat exactly on a second run.

    `terms` and `close` carry the reason of each Paper. A ranking that knows
    neither leaves both out, and the card then has nothing to print for it.
    """
    places = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    return [
        Ranked(
            paper_id=paper_id,
            score=score,
            terms=(terms or {}).get(paper_id, ()),
            meaning_is_close=paper_id in (close or set()),
        )
        for paper_id, score in places
    ]


def keep_reasons(ranked: list[Ranked], source: list[Ranked]) -> list[Ranked]:
    """Returns the ranking with the reasons of another ranking written on it.

    The reranker reorders Papers and knows nothing about stems, so the
    reordered row would otherwise lose the reason the fusion already held.
    """
    reasons = {item.paper_id: item for item in source}
    carried = []
    for item in ranked:
        reason = reasons.get(item.paper_id)
        if reason is None:
            carried.append(item)
            continue
        carried.append(replace(item, terms=reason.terms, meaning_is_close=reason.meaning_is_close))
    return carried


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
                # The stems the card prints. They are collected here and not in
                # a second pass, because this loop already knows which word of
                # the query this Paper holds.
                matched.append(word)
            # The Lucene form of the inverse document frequency. The 1 inside
            # the logarithm keeps it positive, so a word in every document
            # adds nothing instead of subtracting.
            idf = math.log(1 + (total - held_by + 0.5) / (held_by + 0.5))
            # A long document needs more matches to score the same, because a
            # word in a 300 word abstract says less than one in a title.
            weight = BM25_K1 * (1 - BM25_B + BM25_B * length / average_length)
            score += idf * frequency * (BM25_K1 + 1) / (frequency + weight)
        scores[paper_id] = score
        terms[paper_id] = tuple(matched)
    return ordered(scores, terms=terms)


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


def dense_ranking(query: str, papers: list[Paper], embed: Embed, cut: int = CUT) -> list[Ranked]:
    """Ranks the pool by meaning, with one embedding call for the whole pool.

    The query and the documents are two calls, because a vendor embeds a query
    and a document differently.

    The first `cut` Papers are marked as a close meaning, which is the fact the
    card prints for a Paper that holds no word of the query. The cut and not a
    score threshold, because a cosine similarity has no value that means close
    across models, and the cut is the line that already decides a Project.
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
    by_meaning = ordered(scores)
    return [replace(item, meaning_is_close=place < cut) for place, item in enumerate(by_meaning)]


def fuse(rankings: list[list[Ranked]], k: int = RRF_K) -> list[Ranked]:
    """Merges several rankings with reciprocal rank fusion.

    Fusion reads the place of a Paper and never its score, which is why it can
    merge a BM25 score and a cosine similarity at all. The two are numbers on
    different scales, and adding them would let whichever runs larger decide
    every order.
    """
    scores: dict[str, float] = {}
    # The reason of a Paper is carried, because the fused row is the row that
    # ships and a card under it has to say why the Paper is there. The terms
    # come from the keyword ranking and the close meaning from the dense one,
    # so a merge of the two loses neither.
    terms: dict[str, tuple[str, ...]] = {}
    close: set[str] = set()
    for ranking in rankings:
        for place, item in enumerate(ranking, start=1):
            scores[item.paper_id] = scores.get(item.paper_id, 0.0) + 1 / (k + place)
            if item.terms:
                terms[item.paper_id] = item.terms
            if item.meaning_is_close:
                close.add(item.paper_id)
    return ordered(scores, terms=terms, close=close)


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

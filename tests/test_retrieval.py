"""The ranking has to order a pool, keep every Paper in it, and never tie by luck.

Recall at 20 reads the order of the whole pool, so a Paper that matches no
query term still has to appear. These tests pass the embedding function in, so
nothing here reaches the network.
"""

import pytest

from fynd.models import Paper
from fynd.retrieval import (
    bm25_ranking,
    cosine,
    dense_ranking,
    document_text,
    matched_terms,
    stem,
    tokens,
)


def paper(paper_id: str, title: str, abstract: str = "") -> Paper:
    return Paper(paper_id=paper_id, title=title, abstract=abstract)


def ids(ranked) -> list[str]:
    return [item.paper_id for item in ranked]


def fake_embed(vectors: dict[str, list[float]], calls: list):
    """Returns an embedding function that answers from a table of vectors."""

    def embed(texts: list[str], input_type: str) -> list[list[float]]:
        calls.append((texts, input_type))
        return [vectors[text] for text in texts]

    return embed


# The word rules


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        # An ending comes off, so two forms of a word match each other.
        ("households", "household"),
        ("forecasting", "forecast"),
        ("forecasts", "forecast"),
        ("forecasted", "forecast"),
        # Stripping the s from gas leaves two letters and a word that means nothing.
        ("gas", "gas"),
        ("uses", "uses"),
        # Taking the s off "process" would leave "proces" while "processing"
        # leaves "process", so the two forms would stop matching.
        ("process", "process"),
        ("processing", "process"),
        ("processes", "process"),
        ("business", "business"),
        ("businesses", "business"),
        ("analysis", "analysis"),
    ],
)
def test_a_word_keeps_an_ending_only_when_removing_it_leaves_a_real_word(
    word: str, expected: str
) -> None:
    assert stem(word) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("UK Households: energy (demand), 2024!", ["uk", "household", "energy", "demand", "2024"]),
        # A title holds an author name and a place name. Split on the letter u,
        # "Müller" would leave two fragments that match nothing and still count
        # towards the length of the document.
        ("Müller studied São Paulo", ["müller", "studi", "são", "paulo"]),
    ],
)
def test_tokens_lowercase_drop_punctuation_and_keep_accented_words_whole(
    text: str, expected: list[str]
) -> None:
    assert tokens(text) == expected


def test_the_document_is_the_title_and_the_abstract() -> None:
    assert document_text(paper("a", "A title", "An abstract.")) == "A title An abstract."


def test_matched_terms_reads_the_query_order() -> None:
    assert matched_terms("energy household", "A household and its energy") == (
        "energy",
        "household",
    )
    assert matched_terms("household energy", "Ultra-processed food") == ()


# The keyword ranking


def test_bm25_puts_the_matching_paper_first() -> None:
    pool = [
        paper("miss", "Ultra-processed food and health outcomes"),
        paper("hit", "Household energy demand forecasting in the United Kingdom"),
    ]
    assert ids(bm25_ranking("household energy forecasting", pool))[0] == "hit"


def test_bm25_keeps_every_paper_in_the_pool() -> None:
    # A Paper that matches nothing still has to be ranked. Recall at 20 cuts the
    # pool at 20, so a pool the ranking dropped would hide Papers from the cut.
    pool = [paper("miss", "Ultra-processed food"), paper("hit", "Household energy")]
    ranked = bm25_ranking("household energy", pool)
    assert sorted(ids(ranked)) == ["hit", "miss"]
    assert ranked[-1].paper_id == "miss"
    assert ranked[-1].score == 0.0


def test_bm25_counts_a_rare_word_for_more_than_a_common_one() -> None:
    # Every Paper says energy and one says forecasting, so the word that
    # separates the pool is the one that decides the order.
    pool = [
        paper("common", "Energy energy energy energy"),
        paper("rare", "Energy and forecasting"),
    ]
    assert ids(bm25_ranking("energy forecasting", pool))[0] == "rare"


def test_bm25_breaks_a_tie_by_identifier() -> None:
    # Two Papers with the same text score the same. The order then has to come
    # from the identifier, because a published number must repeat exactly.
    pool = [paper("bbb", "Household energy"), paper("aaa", "Household energy")]
    assert ids(bm25_ranking("household energy", pool)) == ["aaa", "bbb"]


def test_bm25_over_an_empty_pool_is_empty() -> None:
    assert bm25_ranking("household energy", []) == []


def test_a_paper_carries_the_stems_it_matched() -> None:
    # The card prints these words, so they come back in the order the query
    # wrote them and not in the order the abstract did.
    pool = [paper("hit", "Forecasting the energy use of a household")]
    ranked = bm25_ranking("household energy forecasting", pool)
    assert ranked[0].terms == ("household", "energy", "forecast")


def test_a_stem_is_named_once_however_often_it_appears() -> None:
    pool = [paper("hit", "Household household households")]
    assert bm25_ranking("household", pool)[0].terms == ("household",)


def test_a_paper_that_matched_no_stem_says_so() -> None:
    pool = [paper("miss", "Ultra-processed food"), paper("hit", "Household energy")]
    ranked = bm25_ranking("household energy", pool)
    # Ordered last, and the empty tuple is what the card reads as no match.
    assert ranked[-1].paper_id == "miss"
    assert ranked[-1].terms == ()


def test_the_keyword_ranking_claims_nothing_about_meaning() -> None:
    pool = [paper("hit", "Household energy")]
    assert bm25_ranking("household energy", pool)[0].meaning_is_close is False


# The meaning ranking


def test_dense_ranking_puts_the_closest_vector_first() -> None:
    near = paper("near", "Household energy")
    far = paper("far", "Ultra-processed food")
    vectors = {
        "household energy forecasting": [1.0, 0.0],
        document_text(near): [0.9, 0.1],
        document_text(far): [0.0, 1.0],
    }

    ranked = dense_ranking("household energy forecasting", [far, near], fake_embed(vectors, []))

    assert ids(ranked) == ["near", "far"]


def test_dense_ranking_asks_for_a_query_and_for_documents() -> None:
    # Voyage scores a query against a document, and the two input types are not
    # the same vector. Sending both as documents measures the wrong thing.
    one = paper("one", "Household energy")
    vectors = {"household energy": [1.0, 0.0], document_text(one): [1.0, 0.0]}
    calls: list = []

    dense_ranking("household energy", [one], fake_embed(vectors, calls))

    assert [input_type for _, input_type in calls] == ["query", "document"]
    assert calls[0][0] == ["household energy"]
    assert calls[1][0] == [document_text(one)]


def test_dense_ranking_over_an_empty_pool_asks_for_nothing() -> None:
    calls: list = []
    assert dense_ranking("household energy", [], fake_embed({}, calls)) == []
    assert calls == []


def test_the_meaning_ranking_marks_the_papers_inside_the_cut() -> None:
    near = paper("near", "Domestic electricity use")
    far = paper("far", "Ultra-processed food")
    vectors = {
        "household energy": [1.0, 0.0],
        document_text(near): [0.9, 0.1],
        document_text(far): [0.0, 1.0],
    }

    ranked = dense_ranking("household energy", [near, far], fake_embed(vectors, []), cut=1)

    assert ranked[0].meaning_is_close is True
    assert ranked[1].meaning_is_close is False
    # The meaning ranking names no stem. It read a vector and not a word.
    assert ranked[0].terms == ()


def test_two_vector_sizes_cannot_be_compared() -> None:
    # The table reports this model at 1024 and at 512, so one run holds both.
    with pytest.raises(ValueError, match="same size"):
        cosine([1.0, 0.0, 0.0, 0.0], [1.0, 0.0])


def test_a_short_embedding_answer_stops_the_ranking() -> None:
    # Zipping a short answer would drop the last Papers, and a recall number
    # would then be measured over fewer Papers than were graded.
    one = paper("one", "Household energy")
    two = paper("two", "Household demand")

    def short_embed(texts: list[str], input_type: str) -> list[list[float]]:
        return [[1.0]]

    with pytest.raises(ValueError, match="do not describe the same Papers"):
        dense_ranking("household energy", [one, two], short_embed)

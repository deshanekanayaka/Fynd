"""The ranking has to order a pool, keep every Paper in it, and never tie by luck.

Recall at 20 reads the order of the whole pool, so a Paper that matches no
query term still has to appear. These tests pass the embedding function and the
reranker in, so nothing here reaches the network.
"""

import pytest

from fynd.models import Paper
from fynd.retrieval import (
    RRF_K,
    Ranked,
    bm25_ranking,
    cosine,
    dense_ranking,
    document_text,
    fuse,
    rerank_ranking,
    stem,
    tokens,
)


def paper(paper_id: str, title: str, abstract: str = "") -> Paper:
    return Paper(paper_id=paper_id, title=title, abstract=abstract)


def ids(ranked) -> list[str]:
    return [item.paper_id for item in ranked]


def test_a_word_loses_a_plural_and_a_verb_ending() -> None:
    assert stem("households") == "household"
    assert stem("forecasting") == "forecast"
    assert stem("forecasts") == "forecast"
    assert stem("forecasted") == "forecast"


def test_a_short_word_keeps_its_ending() -> None:
    # Stripping the s from gas leaves two letters and a word that means nothing.
    assert stem("gas") == "gas"
    assert stem("uses") == "uses"


def test_tokens_lowercase_and_drop_punctuation() -> None:
    assert tokens("UK Households: energy (demand), 2024!") == [
        "uk",
        "household",
        "energy",
        "demand",
        "2024",
    ]


def test_the_document_is_the_title_and_the_abstract() -> None:
    assert document_text(paper("a", "A title", "An abstract.")) == "A title An abstract."


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


def fake_embed(vectors: dict[str, list[float]], calls: list):
    """Returns an embedding function that answers from a table of vectors."""

    def embed(texts: list[str], input_type: str) -> list[list[float]]:
        calls.append((texts, input_type))
        return [vectors[text] for text in texts]

    return embed


def test_dense_ranking_puts_the_closest_vector_first() -> None:
    near = paper("near", "Household energy")
    far = paper("far", "Ultra-processed food")
    vectors = {
        "household energy forecasting": [1.0, 0.0],
        document_text(near): [0.9, 0.1],
        document_text(far): [0.0, 1.0],
    }
    calls: list = []

    ranked = dense_ranking("household energy forecasting", [far, near], fake_embed(vectors, calls))

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


def ranking(*paper_ids: str) -> list[Ranked]:
    """Builds a ranking in the given order. Fusion reads the order and not the score."""
    return [Ranked(paper_id=paper_id, score=1.0) for paper_id in paper_ids]


def test_fusion_adds_one_over_k_plus_the_rank() -> None:
    fused = fuse([ranking("a"), ranking("a")])
    # Rank 1 in both rankings, so the score is twice 1 over k plus 1.
    assert fused[0].paper_id == "a"
    assert fused[0].score == 2 * (1 / (RRF_K + 1))


def test_fusion_prefers_the_paper_both_rankings_like() -> None:
    fused = fuse([ranking("both", "one"), ranking("both", "two")])
    assert fused[0].paper_id == "both"


def test_fusion_keeps_a_paper_only_one_ranking_holds() -> None:
    fused = fuse([ranking("a"), ranking("b")])
    assert sorted(ids(fused)) == ["a", "b"]


def test_fusion_breaks_a_tie_by_identifier() -> None:
    fused = fuse([ranking("bbb"), ranking("aaa")])
    assert ids(fused) == ["aaa", "bbb"]


def fake_rerank(order: list[tuple[int, float]], calls: list):
    """Returns a reranker that answers with a fixed order of indexes."""

    def rerank(query: str, documents: list[str]) -> list[tuple[int, float]]:
        calls.append((query, documents))
        return order

    return rerank


def test_the_reranker_reorders_the_papers_it_was_given() -> None:
    first = paper("first", "Household energy")
    second = paper("second", "Ultra-processed food")
    calls: list = []

    # The reranker says the second document is the better one.
    ranked = rerank_ranking(
        "household energy", [first, second], fake_rerank([(1, 0.9), (0, 0.2)], calls)
    )

    assert ids(ranked) == ["second", "first"]
    assert calls[0][0] == "household energy"
    assert calls[0][1] == [document_text(first), document_text(second)]


def test_the_reranker_is_not_called_for_an_empty_pool() -> None:
    calls: list = []
    assert rerank_ranking("household energy", [], fake_rerank([], calls)) == []
    assert calls == []


def test_an_s_that_is_part_of_the_word_stays() -> None:
    # The whole point of the rule is that two forms of a word match. Taking the
    # s off "process" would leave "proces" while "processing" leaves "process",
    # so the two would stop matching.
    assert stem("process") == stem("processing") == stem("processes") == "process"
    assert stem("business") == stem("businesses") == "business"
    assert stem("analysis") == "analysis"


def test_an_accented_word_stays_one_word() -> None:
    # A title holds an author name and a place name. Split on the letter u,
    # "Müller" would leave two fragments that match nothing and still count
    # towards the length of the document.
    assert tokens("Müller studied São Paulo") == ["müller", "studi", "são", "paulo"]


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
        return [[1.0]] if input_type == "query" else [[1.0]]

    with pytest.raises(ValueError, match="do not describe the same Papers"):
        dense_ranking("household energy", [one, two], short_embed)


def test_the_reranker_breaks_a_tie_by_identifier() -> None:
    # The vendor's own order for two equal scores is not repeatable, and a
    # published number has to be.
    first = paper("bbb", "Household energy")
    second = paper("aaa", "Household demand")
    calls: list = []

    ranked = rerank_ranking(
        "household energy", [first, second], fake_rerank([(0, 0.5), (1, 0.5)], calls)
    )

    assert ids(ranked) == ["aaa", "bbb"]


def test_a_paper_the_reranker_skipped_ranks_last() -> None:
    kept = paper("kept", "Household energy")
    skipped = paper("skipped", "Ultra-processed food")
    calls: list = []

    ranked = rerank_ranking("household energy", [kept, skipped], fake_rerank([(0, 0.4)], calls))

    assert ids(ranked) == ["kept", "skipped"]
    assert ranked[-1].score == 0.0


def test_a_place_outside_the_pool_stops_the_ranking() -> None:
    # The index arrives from outside Fynd. A negative one would count backwards
    # from the end of the pool and score the wrong Paper in silence.
    one = paper("one", "Household energy")
    calls: list = []

    with pytest.raises(ValueError, match="does not describe the pool"):
        rerank_ranking("household energy", [one], fake_rerank([(-1, 0.9)], calls))

    with pytest.raises(ValueError, match="does not describe the pool"):
        rerank_ranking("household energy", [one], fake_rerank([(7, 0.9)], calls))

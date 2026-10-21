"""The embedding client has to cache one vector per text and count its tokens.

A batch cached as one blob would pay for all 60 abstracts again when one Paper
joins the pool, so the cache holds one text at a time.
"""

import httpx
import pytest

from fynd.voyage import (
    BASE_URL,
    DIMENSIONS,
    EMBEDDING_MODEL,
    RERANK_MODEL,
    KeyMissing,
    RateLimited,
    ReplyIncomplete,
    Voyage,
)


def client_that_returns(replies: list, calls: list) -> httpx.Client:
    """Builds an httpx client that answers each request from the list in turn."""

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        status, reply = replies[min(len(calls) - 1, len(replies) - 1)]
        return httpx.Response(status, json=reply)

    return httpx.Client(transport=httpx.MockTransport(handler))


def embedding_reply(vectors: list[list[float]], tokens: int = 7) -> tuple[int, dict]:
    data = [{"index": place, "embedding": vector} for place, vector in enumerate(vectors)]
    return 200, {"data": data, "model": EMBEDDING_MODEL, "usage": {"total_tokens": tokens}}


def test_a_vector_comes_back_for_every_text(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("VOYAGE_API_KEY", "al-test-key")
    calls: list = []
    voyage = Voyage(client=client_that_returns([embedding_reply([[1.0], [2.0]])], calls))

    vectors = voyage.embed(["one", "two"], input_type="document")

    assert vectors == [[1.0], [2.0]]
    assert len(calls) == 1


def test_the_request_names_the_model_the_type_and_the_size(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("VOYAGE_API_KEY", "al-test-key")
    calls: list = []
    voyage = Voyage(client=client_that_returns([embedding_reply([[1.0]])], calls))

    voyage.embed(["one"], input_type="query")

    # The host is pinned, because an Atlas key is refused by the voyageai.com
    # host and the other way round, and both answer the same two paths.
    assert str(calls[0].url) == f"{BASE_URL}/embeddings"
    sent = calls[0].read().decode("utf-8")
    assert EMBEDDING_MODEL in sent
    assert '"input_type":"query"' in sent
    assert str(DIMENSIONS) in sent
    assert calls[0].headers["authorization"] == "Bearer al-test-key"


def test_a_second_run_asks_for_nothing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("VOYAGE_API_KEY", "al-test-key")
    calls: list = []
    voyage = Voyage(client=client_that_returns([embedding_reply([[1.0]])], calls))

    voyage.embed(["one"], input_type="document")
    second = voyage.embed(["one"], input_type="document")

    assert second == [[1.0]]
    assert len(calls) == 1


def test_only_the_new_text_is_sent(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("VOYAGE_API_KEY", "al-test-key")
    calls: list = []
    replies = [embedding_reply([[1.0]]), embedding_reply([[2.0]])]
    voyage = Voyage(client=client_that_returns(replies, calls))

    voyage.embed(["one"], input_type="document")
    both = voyage.embed(["one", "two"], input_type="document")

    # One Paper joined the pool, so one text is paid for and the order holds.
    assert both == [[1.0], [2.0]]
    assert b"two" in calls[1].read()
    assert b"one" not in calls[1].read()


def test_a_query_and_a_document_are_cached_apart(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("VOYAGE_API_KEY", "al-test-key")
    calls: list = []
    replies = [embedding_reply([[1.0]]), embedding_reply([[9.0]])]
    voyage = Voyage(client=client_that_returns(replies, calls))

    assert voyage.embed(["one"], input_type="query") == [[1.0]]
    assert voyage.embed(["one"], input_type="document") == [[9.0]]


def test_the_tokens_of_a_run_are_counted(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("VOYAGE_API_KEY", "al-test-key")
    calls: list = []
    voyage = Voyage(client=client_that_returns([embedding_reply([[1.0]], tokens=24)], calls))

    voyage.embed(["one"], input_type="document")

    # The README states the measured token count for one Project, so a run has
    # to be able to say what it spent. A cached text spends nothing.
    assert voyage.tokens_used == 24
    voyage.embed(["one"], input_type="document")
    assert voyage.tokens_used == 24


def test_no_text_means_no_request(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("VOYAGE_API_KEY", "al-test-key")
    calls: list = []
    voyage = Voyage(client=client_that_returns([], calls))

    assert voyage.embed([], input_type="document") == []
    assert calls == []


def test_a_missing_key_is_said_in_a_sentence(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    voyage = Voyage(client=client_that_returns([], []))

    with pytest.raises(KeyMissing, match="VOYAGE_API_KEY"):
        voyage.embed(["one"], input_type="document")


def test_the_reranker_returns_places_and_scores(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("VOYAGE_API_KEY", "al-test-key")
    calls: list = []
    reply = (
        200,
        {
            "data": [
                {"index": 1, "relevance_score": 0.9},
                {"index": 0, "relevance_score": 0.2},
            ],
            "usage": {"total_tokens": 11},
        },
    )
    voyage = Voyage(client=client_that_returns([reply], calls))

    answer = voyage.rerank("household energy", ["far", "near"])

    assert answer == [(1, 0.9), (0, 0.2)]
    assert RERANK_MODEL in calls[0].read().decode("utf-8")
    assert voyage.tokens_used == 11


def test_a_reranked_list_is_cached(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("VOYAGE_API_KEY", "al-test-key")
    calls: list = []
    reply = (200, {"data": [{"index": 0, "relevance_score": 0.5}], "usage": {}})
    voyage = Voyage(client=client_that_returns([reply], calls))

    voyage.rerank("household energy", ["one"])
    assert voyage.rerank("household energy", ["one"]) == [(0, 0.5)]
    assert len(calls) == 1


def test_two_refusals_in_a_row_raise(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("VOYAGE_API_KEY", "al-test-key")
    monkeypatch.setattr("fynd.voyage.time.sleep", lambda seconds: None)
    calls: list = []
    voyage = Voyage(client=client_that_returns([(429, {"detail": "slow down"})], calls))

    with pytest.raises(RateLimited):
        voyage.embed(["one"], input_type="document")
    assert len(calls) == 2


def test_a_refused_request_caches_nothing(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("VOYAGE_API_KEY", "al-test-key")
    monkeypatch.setattr("fynd.voyage.time.sleep", lambda seconds: None)
    calls: list = []
    replies = [(429, {"detail": "slow down"})]
    voyage = Voyage(client=client_that_returns(replies, calls))

    with pytest.raises(RateLimited):
        voyage.embed(["one"], input_type="document")

    # A cached refusal would serve a missing vector to every later run.
    replies.append(embedding_reply([[3.0]]))
    assert Voyage(client=client_that_returns(replies[1:], [])).embed(
        ["one"], input_type="document"
    ) == [[3.0]]


def test_an_empty_reranked_list_is_not_cached(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("VOYAGE_API_KEY", "al-test-key")
    calls: list = []
    replies = [(200, {"data": [], "usage": {}})]
    voyage = Voyage(client=client_that_returns(replies, calls))

    with pytest.raises(ReplyIncomplete, match="scored none"):
        voyage.rerank("household energy", ["one"])

    # Cached, an empty answer would serve an empty ranking to every later run,
    # and a second run could not fix it.
    replies.append((200, {"data": [{"index": 0, "relevance_score": 0.5}], "usage": {}}))
    assert Voyage(client=client_that_returns(replies[1:], [])).rerank(
        "household energy", ["one"]
    ) == [(0, 0.5)]


def test_a_missing_vector_is_said_without_the_text(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("VOYAGE_API_KEY", "al-test-key")
    calls: list = []
    voyage = Voyage(client=client_that_returns([embedding_reply([[1.0]])], calls))

    with pytest.raises(ReplyIncomplete) as refused:
        voyage.embed(["one", "an abstract that must stay out of a log"], input_type="document")

    # An abstract in a traceback is an abstract in a log file, and ADR 0011
    # keeps the text out.
    assert "abstract that must stay out" not in str(refused.value)
    assert "1 of 2" in str(refused.value)


def test_a_key_from_the_wrong_place_is_said_in_a_sentence(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    # A key made at voyageai.com carries another prefix, and the Atlas host
    # answers it with a 401 that explains nothing.
    monkeypatch.setenv("VOYAGE_API_KEY", "pa-a-key-made-at-voyageai-com")
    voyage = Voyage(client=client_that_returns([], []))

    with pytest.raises(KeyMissing, match="not made in MongoDB Atlas"):
        voyage.embed(["one"], input_type="document")


def test_the_reranker_is_asked_at_the_same_host(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("VOYAGE_API_KEY", "al-test-key")
    calls: list = []
    reply = (200, {"data": [{"index": 0, "relevance_score": 0.5}], "usage": {}})
    voyage = Voyage(client=client_that_returns([reply], calls))

    voyage.rerank("household energy", ["one"])

    assert str(calls[0].url) == f"{BASE_URL}/rerank"
    sent = calls[0].read().decode("utf-8")
    # The three fields the endpoint reads, which are not the fields of the
    # embeddings endpoint.
    assert '"query":"household energy"' in sent
    assert '"documents":["one"]' in sent

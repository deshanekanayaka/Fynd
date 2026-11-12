"""The embedding client has to cache one vector per text and count its tokens.

A batch cached as one blob would pay for all 60 abstracts again when one Paper
joins the pool, so the cache holds one text at a time.
"""

import httpx
import pytest

from fynd.voyage import (
    BASE_URL,
    CHARACTERS_PER_TOKEN,
    DIMENSIONS,
    EMBEDDING_MODEL,
    MIN_SECONDS_BETWEEN_REQUESTS,
    SLICE_TOKENS,
    KeyMissing,
    RateLimited,
    ReplyIncomplete,
    Voyage,
    slices,
)


@pytest.fixture(autouse=True)
def a_key(monkeypatch):
    """Gives every test a key with the prefix this client expects.

    The two tests about a bad key set their own, which wins, because a test
    body runs after the fixture.
    """
    monkeypatch.setenv("VOYAGE_API_KEY", "al-test-key")


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


def client_for(replies: list, calls: list | None = None) -> Voyage:
    """Builds a client that answers from a list of replies."""
    return Voyage(client=client_that_returns(replies, calls if calls is not None else []))


def test_a_vector_comes_back_for_every_text() -> None:
    calls: list = []
    voyage = client_for([embedding_reply([[1.0], [2.0]])], calls)

    vectors = voyage.embed(["one", "two"], input_type="document")

    assert vectors == [[1.0], [2.0]]
    assert len(calls) == 1


def test_the_request_names_the_model_the_type_and_the_size() -> None:
    calls: list = []
    voyage = client_for([embedding_reply([[1.0]])], calls)

    voyage.embed(["one"], input_type="query")

    # Send embeddings to the configured Atlas endpoint with its expected request fields.
    assert str(calls[0].url) == f"{BASE_URL}/embeddings"
    sent = calls[0].read().decode("utf-8")
    assert EMBEDDING_MODEL in sent
    assert '"input_type":"query"' in sent
    assert str(DIMENSIONS) in sent
    assert calls[0].headers["authorization"] == "Bearer al-test-key"


def test_a_second_run_asks_for_nothing() -> None:
    calls: list = []
    voyage = client_for([embedding_reply([[1.0]])], calls)

    voyage.embed(["one"], input_type="document")
    second = voyage.embed(["one"], input_type="document")

    assert second == [[1.0]]
    assert len(calls) == 1


def test_only_the_new_text_is_sent() -> None:
    calls: list = []
    replies = [embedding_reply([[1.0]]), embedding_reply([[2.0]])]
    voyage = Voyage(client=client_that_returns(replies, calls))

    voyage.embed(["one"], input_type="document")
    both = voyage.embed(["one", "two"], input_type="document")

    # One Paper joined the pool, so one text is paid for and the order holds.
    assert both == [[1.0], [2.0]]
    assert b"two" in calls[1].read()
    assert b"one" not in calls[1].read()


def test_a_query_and_a_document_are_cached_apart() -> None:
    calls: list = []
    replies = [embedding_reply([[1.0]]), embedding_reply([[9.0]])]
    voyage = Voyage(client=client_that_returns(replies, calls))

    assert voyage.embed(["one"], input_type="query") == [[1.0]]
    assert voyage.embed(["one"], input_type="document") == [[9.0]]


def test_the_tokens_of_a_run_are_counted() -> None:
    calls: list = []
    voyage = client_for([embedding_reply([[1.0]], tokens=24)], calls)

    voyage.embed(["one"], input_type="document")

    # Cache hits must not increase this client's reported token usage.
    assert voyage.tokens_used == 24
    voyage.embed(["one"], input_type="document")
    assert voyage.tokens_used == 24


def test_no_text_means_no_request() -> None:
    calls: list = []
    voyage = client_for([], calls)

    assert voyage.embed([], input_type="document") == []
    assert calls == []


def test_a_missing_key_is_said_in_a_sentence(monkeypatch) -> None:
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    voyage = client_for([])

    with pytest.raises(KeyMissing, match="VOYAGE_API_KEY"):
        voyage.embed(["one"], input_type="document")


def test_two_refusals_in_a_row_raise() -> None:
    calls: list = []
    voyage = client_for([(429, {"detail": "slow down"})], calls)

    with pytest.raises(RateLimited):
        voyage.embed(["one"], input_type="document")
    assert len(calls) == 2


def test_a_refused_request_caches_nothing() -> None:
    calls: list = []
    replies = [(429, {"detail": "slow down"})]
    voyage = Voyage(client=client_that_returns(replies, calls))

    with pytest.raises(RateLimited):
        voyage.embed(["one"], input_type="document")

    # A cached refusal would serve a missing vector to every later run.
    replies.append(embedding_reply([[3.0]]))
    assert client_for(replies[1:]).embed(["one"], input_type="document") == [[3.0]]


def test_a_missing_vector_is_said_without_the_text() -> None:
    calls: list = []
    voyage = client_for([embedding_reply([[1.0]])], calls)

    with pytest.raises(ReplyIncomplete) as refused:
        voyage.embed(["one", "an abstract that must stay out of a log"], input_type="document")

    # An abstract in a traceback is an abstract in a log file, and ADR 0011
    # keeps the text out.
    assert "abstract that must stay out" not in str(refused.value)
    assert "1 of 2" in str(refused.value)


def test_a_key_from_the_wrong_place_is_said_in_a_sentence(monkeypatch) -> None:
    # Key validation should fail before sending a request to an incompatible endpoint.
    monkeypatch.setenv("VOYAGE_API_KEY", "pa-a-key-made-at-voyageai-com")
    voyage = client_for([])

    with pytest.raises(KeyMissing, match="not made in MongoDB Atlas"):
        voyage.embed(["one"], input_type="document")


def test_a_long_pool_is_cut_into_slices_under_the_token_budget() -> None:
    # Check local batch grouping independently of any live service limits.
    budget = SLICE_TOKENS * CHARACTERS_PER_TOKEN
    texts = ["x" * budget, "y" * (budget // 2), "z" * 4]

    groups = slices(texts)

    # The first text fills a slice by itself, and the other two share one.
    assert groups == [[texts[0]], [texts[1], texts[2]]]


def test_a_text_longer_than_the_budget_travels_alone() -> None:
    # Dropping it would leave a Paper of the pool with no vector, and the
    # recall number would then be measured over fewer Papers than were graded.
    assert slices(["w" * 80_000]) == [["w" * 80_000]]


def test_each_slice_is_one_request_and_the_client_paces_itself(monkeypatch) -> None:
    waits: list[float] = []
    monkeypatch.setattr("fynd.voyage.time.sleep", waits.append)
    long_one = "a" * (SLICE_TOKENS * CHARACTERS_PER_TOKEN)
    long_two = "b" * (SLICE_TOKENS * CHARACTERS_PER_TOKEN)
    calls: list = []
    voyage = client_for([embedding_reply([[1.0]])], calls)

    vectors = voyage.embed([long_one, long_two], input_type="document")

    assert vectors == [[1.0], [1.0]]
    assert len(calls) == 2
    # The first request is immediate; the second waits out the configured 21-second gap.
    assert len(waits) == 1
    assert 0 < waits[0] <= MIN_SECONDS_BETWEEN_REQUESTS

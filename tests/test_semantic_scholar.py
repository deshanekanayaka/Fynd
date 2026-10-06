"""The search client has to parse the API, count open copies, and use the cache."""

import httpx
import pytest

from fynd.semantic_scholar import RateLimited, SemanticScholar

# One recorded response, trimmed to the fields Fynd asks for.
RECORDED_RESPONSE = {
    "total": 2,
    "data": [
        {
            "paperId": "aaa",
            "title": "Short term load forecasting for United Kingdom households",
            "abstract": "We forecast household demand.",
            "year": 2023,
            "externalIds": {"ArXiv": "2301.00001"},
            "openAccessPdf": {"url": "https://arxiv.org/pdf/2301.00001"},
        },
        {
            "paperId": "bbb",
            "title": "A paywalled study of fuel poverty",
            "abstract": None,
            "year": None,
            "externalIds": None,
            "openAccessPdf": None,
        },
    ],
}


def fake_client(calls: list[httpx.Request]) -> httpx.Client:
    """Return a client that answers with the recorded response and counts the calls."""

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=RECORDED_RESPONSE)

    return httpx.Client(transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def cache_in_a_temporary_directory(tmp_path, monkeypatch):
    # Every test gets an empty cache, so one test cannot feed another.
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)


def test_search_parses_a_paper_and_tolerates_a_missing_field():
    result = SemanticScholar(client=fake_client([])).search("energy", limit=2)

    assert result.total == 2
    assert len(result.papers) == 2

    first = result.papers[0]
    assert first.arxiv_id == "2301.00001"
    assert first.has_open_copy is True

    # The second item has null for three fields, which the API really does return.
    second = result.papers[1]
    assert second.abstract == ""
    assert second.year is None
    assert second.has_open_copy is False


def test_open_copy_count_is_what_stage_2_checks():
    result = SemanticScholar(client=fake_client([])).search("energy", limit=2)
    assert result.open_copy_count == 1


def test_the_second_search_uses_the_cache_and_makes_no_request():
    calls: list[httpx.Request] = []
    client = SemanticScholar(client=fake_client(calls))

    client.search("energy", limit=2)
    client.search("energy", limit=2)

    assert len(calls) == 1


def test_the_api_key_is_sent_as_a_header(monkeypatch):
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "test-key")
    calls: list[httpx.Request] = []

    SemanticScholar(client=fake_client(calls)).search("energy", limit=2)

    assert calls[0].headers["x-api-key"] == "test-key"


def test_a_429_answer_is_retried_once_and_then_raises(monkeypatch):
    # The wait is real time, so the test replaces it.
    monkeypatch.setattr("fynd.semantic_scholar.RETRY_WAIT_SECONDS", 0.0)
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(429)

    client = SemanticScholar(client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(RateLimited):
        client.search("energy", limit=2)

    assert len(calls) == 2


def test_a_429_answer_is_not_cached(monkeypatch):
    monkeypatch.setattr("fynd.semantic_scholar.RETRY_WAIT_SECONDS", 0.0)
    answers = [
        httpx.Response(429),
        httpx.Response(429),
        httpx.Response(200, json=RECORDED_RESPONSE),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return answers.pop(0)

    client = SemanticScholar(client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(RateLimited):
        client.search("energy", limit=2)

    # The failed search must leave nothing behind, or the Topic looks empty forever.
    result = client.search("energy", limit=2)
    assert len(result.papers) == 2

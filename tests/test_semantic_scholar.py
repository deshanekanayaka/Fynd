"""The search client has to parse the API, ask for the Evidence window, and cache."""

import httpx
import pytest

from fynd.semantic_scholar import RateLimited, SemanticScholar

# One recorded reply, trimmed to the fields Fynd asks for.
RECORDED_REPLY = {
    "total": 2,
    "data": [
        {
            "paperId": "aaa",
            "title": "Short term load forecasting for United Kingdom households",
            "abstract": "We forecast household demand.",
            "year": 2023,
            "externalIds": {"DOI": "10.1000/aaa"},
            "openAccessPdf": {"url": "https://dro.dur.ac.uk/aaa.pdf"},
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


def client_that_returns(reply: dict, calls: list) -> httpx.Client:
    """Builds an httpx client that answers every request from memory."""

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json=reply)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_a_paper_keeps_the_fields_fynd_uses(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    calls: list = []
    search = SemanticScholar(client=client_that_returns(RECORDED_REPLY, calls))

    result = search.search("uk household energy forecasting", year_from=2022)

    assert result.total == 2
    assert len(result.papers) == 2
    first = result.papers[0]
    assert first.paper_id == "aaa"
    assert first.doi == "10.1000/aaa"
    assert first.open_copy_url == "https://dro.dur.ac.uk/aaa.pdf"
    assert first.has_open_copy is True


def test_a_missing_field_becomes_a_default(tmp_path, monkeypatch) -> None:
    # The API leaves a field out or sets it to null, and neither must raise.
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    search = SemanticScholar(client=client_that_returns(RECORDED_REPLY, []))

    second = search.search("anything", year_from=2022).papers[1]

    assert second.abstract == ""
    assert second.doi == ""
    assert second.year is None
    assert second.has_open_copy is False


def test_the_open_copy_count_is_what_stage_2_reads(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    search = SemanticScholar(client=client_that_returns(RECORDED_REPLY, []))

    assert search.search("anything", year_from=2022).open_copy_count == 1


def test_the_request_asks_for_the_evidence_window(tmp_path, monkeypatch) -> None:
    # ADR 0008 puts the year range in the search, so the recent pool is as large
    # as the API makes it.
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    calls: list = []
    search = SemanticScholar(client=client_that_returns(RECORDED_REPLY, calls))

    search.search("anything", year_from=2022)

    assert calls[0].url.params["year"] == "2022-"


def test_a_second_run_of_the_same_search_makes_no_request(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    calls: list = []
    search = SemanticScholar(client=client_that_returns(RECORDED_REPLY, calls))

    search.search("anything", year_from=2022)
    search.search("anything", year_from=2022)

    assert len(calls) == 1


def test_a_different_year_range_is_a_different_cache_entry(tmp_path, monkeypatch) -> None:
    # The window is an input, so a run in a new calendar year asks again.
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    calls: list = []
    search = SemanticScholar(client=client_that_returns(RECORDED_REPLY, calls))

    search.search("anything", year_from=2022)
    search.search("anything", year_from=2023)

    assert len(calls) == 2


def test_two_rate_limit_answers_stop_with_a_sentence(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr("fynd.semantic_scholar.RETRY_WAIT_SECONDS", 0)
    calls: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(429, json={"message": "too many requests"})

    search = SemanticScholar(client=httpx.Client(transport=httpx.MockTransport(handler)))

    with pytest.raises(RateLimited) as error:
        search.search("anything", year_from=2022)

    assert len(calls) == 2
    assert "SEMANTIC_SCHOLAR_API_KEY" in str(error.value)


def test_a_failed_search_is_never_cached(tmp_path, monkeypatch) -> None:
    # ADR 0004: a failed reply is never cached, so the next run asks again.
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setattr("fynd.semantic_scholar.RETRY_WAIT_SECONDS", 0)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={})

    search = SemanticScholar(client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(RateLimited):
        search.search("anything", year_from=2022)

    assert list(tmp_path.iterdir()) == []

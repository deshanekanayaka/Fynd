"""The second lookup has to find a repository file, and refuse a publisher."""

import httpx
import pytest

from fynd.contact import ContactEmailMissing
from fynd.openalex import OpenAlex, WorkNotRead

# One recorded reply, trimmed to the fields Fynd reads. A real work carries a
# publisher location and a repository location, and Fynd wants the second.
RECORDED_WORK = {
    "id": "https://openalex.org/W123",
    "doi": "https://doi.org/10.1000/aaa",
    "best_oa_location": {
        "is_oa": True,
        "pdf_url": None,
        "landing_page_url": "https://www.sciencedirect.com/aaa",
        "license": "cc-by",
        "source": {"display_name": "Applied Energy", "type": "journal"},
    },
    "locations": [
        {
            "is_oa": True,
            "pdf_url": None,
            "landing_page_url": "https://www.sciencedirect.com/aaa",
            "license": "cc-by",
            "source": {"display_name": "Applied Energy", "type": "journal"},
        },
        {
            "is_oa": True,
            "pdf_url": "https://dro.dur.ac.uk/aaa.pdf",
            "landing_page_url": "https://dro.dur.ac.uk/aaa",
            "license": "cc-by",
            "source": {"display_name": "Durham Research Online", "type": "repository"},
        },
    ],
}


def client_that_returns(status: int, reply: dict | None, calls: list) -> httpx.Client:
    """Builds an httpx client that answers every request from memory."""

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if reply is None:
            return httpx.Response(status)
        return httpx.Response(status, json=reply)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_the_repository_location_wins_over_the_publisher(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("FYND_CONTACT_EMAIL", "deshan@example.org")
    calls: list = []
    resolver = OpenAlex(client=client_that_returns(200, RECORDED_WORK, calls))

    answer = resolver.resolve("10.1000/aaa")

    assert answer.found is True
    assert answer.open_copy is not None
    assert answer.open_copy.url == "https://dro.dur.ac.uk/aaa.pdf"
    assert answer.open_copy.host == "dro.dur.ac.uk"
    assert answer.open_copy.license == "cc-by"


def test_the_best_location_wins_when_it_is_a_repository(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("FYND_CONTACT_EMAIL", "deshan@example.org")
    work = {
        "best_oa_location": {
            "is_oa": True,
            "pdf_url": "https://arxiv.org/pdf/2201.00001",
            "landing_page_url": "https://arxiv.org/abs/2201.00001",
            "license": "cc-by",
            "source": {"display_name": "arXiv", "type": "repository"},
        },
        "locations": [],
    }
    resolver = OpenAlex(client=client_that_returns(200, work, []))

    answer = resolver.resolve("10.1000/bbb")

    assert answer.open_copy is not None
    assert answer.open_copy.url == "https://arxiv.org/pdf/2201.00001"
    assert answer.open_copy.host == "arxiv.org"


def test_a_work_with_only_a_publisher_location_gives_no_open_copy(tmp_path, monkeypatch) -> None:
    # A found record with no file is a fact about the Paper, and the reason
    # table counts it apart from a Paper OpenAlex never heard of.
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("FYND_CONTACT_EMAIL", "deshan@example.org")
    work = {
        "best_oa_location": None,
        "locations": [
            {
                "is_oa": False,
                "pdf_url": None,
                "landing_page_url": "https://www.sciencedirect.com/ccc",
                "license": None,
                "source": {"display_name": "Applied Energy", "type": "journal"},
            }
        ],
    }
    resolver = OpenAlex(client=client_that_returns(200, work, []))

    answer = resolver.resolve("10.1000/ccc")

    assert answer.found is True
    assert answer.open_copy is None


def test_an_unknown_identifier_is_not_found(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("FYND_CONTACT_EMAIL", "deshan@example.org")
    resolver = OpenAlex(client=client_that_returns(404, None, []))

    answer = resolver.resolve("10.1000/nothing")

    assert answer.found is False
    assert answer.open_copy is None


def test_a_landing_page_is_used_when_there_is_no_pdf_link(tmp_path, monkeypatch) -> None:
    # The fetcher then refuses the page, and the reason table says not a PDF,
    # which is a measured fact and not a guess about the host.
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("FYND_CONTACT_EMAIL", "deshan@example.org")
    work = {
        "best_oa_location": None,
        "locations": [
            {
                "is_oa": True,
                "pdf_url": None,
                "landing_page_url": "https://www.research.ed.ac.uk/ddd",
                "license": "cc-by-nc",
                "source": {"display_name": "Edinburgh Research Explorer", "type": "repository"},
            }
        ],
    }
    resolver = OpenAlex(client=client_that_returns(200, work, []))

    answer = resolver.resolve("10.1000/ddd")

    assert answer.open_copy is not None
    assert answer.open_copy.url == "https://www.research.ed.ac.uk/ddd"


def test_every_answer_is_cached(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("FYND_CONTACT_EMAIL", "deshan@example.org")
    calls: list = []
    resolver = OpenAlex(client=client_that_returns(200, RECORDED_WORK, calls))
    resolver.resolve("10.1000/aaa")
    resolver.resolve("10.1000/aaa")
    assert len(calls) == 1

    missing: list = []
    absent = OpenAlex(client=client_that_returns(404, None, missing))
    absent.resolve("10.1000/nothing")
    absent.resolve("10.1000/nothing")
    assert len(missing) == 1


def test_the_request_carries_the_contact_email(tmp_path, monkeypatch) -> None:
    # OpenAlex serves a request with an email from a faster queue, and a
    # repository administrator must be able to find the operator.
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("FYND_CONTACT_EMAIL", "deshan@example.org")
    calls: list = []
    resolver = OpenAlex(client=client_that_returns(200, RECORDED_WORK, calls))

    resolver.resolve("10.1000/aaa")

    request = calls[0]
    assert request.url.params["mailto"] == "deshan@example.org"
    assert "deshan@example.org" in request.headers["user-agent"]
    assert "Fynd" in request.headers["user-agent"]


def test_a_broken_reply_stops_with_a_sentence(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("FYND_CONTACT_EMAIL", "deshan@example.org")
    resolver = OpenAlex(client=client_that_returns(500, None, []))

    with pytest.raises(WorkNotRead):
        resolver.resolve("10.1000/aaa")


def test_a_broken_reply_is_not_cached(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("FYND_CONTACT_EMAIL", "deshan@example.org")
    broken: list = []
    resolver = OpenAlex(client=client_that_returns(500, None, broken))
    with pytest.raises(WorkNotRead):
        resolver.resolve("10.1000/aaa")

    calls: list = []
    working = OpenAlex(client=client_that_returns(200, RECORDED_WORK, calls))
    answer = working.resolve("10.1000/aaa")

    assert len(calls) == 1
    assert answer.found is True


def test_a_missing_contact_email_stops_the_lookup(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.delenv("FYND_CONTACT_EMAIL", raising=False)
    calls: list = []
    resolver = OpenAlex(client=client_that_returns(200, RECORDED_WORK, calls))

    with pytest.raises(ContactEmailMissing):
        resolver.resolve("10.1000/aaa")
    assert calls == []

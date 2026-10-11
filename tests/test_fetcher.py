"""The fetcher has to obey every rule in ADR 0007, and cache what it learned."""

import httpx
import pytest

from fynd import cache, reasons
from fynd.contact import ContactEmailMissing
from fynd.fetcher import MAX_BYTES, Fetched, Fetcher, FetchFailed, Refused

PDF_BODY = b"%PDF-1.7 a short paper"


@pytest.fixture(autouse=True)
def a_cache_and_an_address(tmp_path, monkeypatch):
    """Gives every test its own cache directory and an operator address."""
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("FYND_CONTACT_EMAIL", "deshan@example.org")
    monkeypatch.setattr("fynd.fetcher.time.sleep", lambda seconds: None)
    return tmp_path


def transport_that_returns(responses: list, calls: list) -> httpx.MockTransport:
    """Builds a transport that answers each request from the list in order."""

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        index = min(len(calls) - 1, len(responses) - 1)
        return responses[index]

    return httpx.MockTransport(handler)


def pdf_response() -> httpx.Response:
    return httpx.Response(200, content=PDF_BODY, headers={"content-type": "application/pdf"})


def test_a_pdf_comes_back_as_bytes() -> None:
    calls: list = []
    fetcher = Fetcher(transport=transport_that_returns([pdf_response()], calls))

    answer = fetcher.fetch("https://dro.dur.ac.uk/aaa.pdf")

    assert isinstance(answer, Fetched)
    assert answer.data == PDF_BODY
    assert answer.content_type == "application/pdf"


def test_a_second_fetch_makes_no_request() -> None:
    calls: list = []
    fetcher = Fetcher(transport=transport_that_returns([pdf_response()], calls))
    fetcher.fetch("https://dro.dur.ac.uk/aaa.pdf")
    fetcher.fetch("https://dro.dur.ac.uk/aaa.pdf")
    assert len(calls) == 1

    # A new run reads the same sidecar, which is what makes the measurement
    # reproducible with no network.
    second = Fetcher(transport=transport_that_returns([pdf_response()], []))
    answer = second.fetch("https://dro.dur.ac.uk/aaa.pdf")
    assert isinstance(answer, Fetched)


def test_pdf_bytes_with_a_wrong_content_type_are_accepted() -> None:
    page = httpx.Response(200, content=PDF_BODY, headers={"content-type": "text/html"})
    fetcher = Fetcher(transport=transport_that_returns([page], []))

    answer = fetcher.fetch("https://pdpublishers.com/aaa")

    assert isinstance(answer, Fetched)


def test_a_login_page_with_a_pdf_name_is_not_a_pdf() -> None:
    # The check that catches it is the first bytes, which are not %PDF.
    page = httpx.Response(
        200, content=b"<html>Please sign in</html>", headers={"content-type": "text/html"}
    )
    fetcher = Fetcher(transport=transport_that_returns([page], []))

    answer = fetcher.fetch("https://www.sciencedirect.com/aaa.pdf")

    assert isinstance(answer, Refused)
    assert answer.reason == reasons.NOT_A_PDF
    assert answer.status == 200


def test_a_refused_host_is_cached() -> None:
    calls: list = []
    forbidden = httpx.Response(403, headers={"content-type": "text/html"})
    fetcher = Fetcher(transport=transport_that_returns([forbidden], calls))

    first = fetcher.fetch("https://www.sciencedirect.com/aaa.pdf")
    second = fetcher.fetch("https://www.sciencedirect.com/aaa.pdf")

    assert isinstance(first, Refused)
    assert first.status == 403
    assert first.reason == reasons.FETCH_REFUSED
    assert second == first
    assert len(calls) == 1


def test_a_body_over_the_cap_is_refused() -> None:
    big = httpx.Response(
        200,
        content=PDF_BODY + b"x" * (MAX_BYTES + 1),
        headers={"content-type": "application/pdf"},
    )
    fetcher = Fetcher(transport=transport_that_returns([big], []))

    answer = fetcher.fetch("https://dro.dur.ac.uk/big.pdf")

    assert isinstance(answer, Refused)
    assert answer.reason == reasons.FETCH_REFUSED


def test_a_fourth_redirect_is_refused() -> None:
    # The limit is 3. A chain that never ends answers nothing, so there is no
    # final status to record.
    hop = httpx.Response(302, headers={"location": "https://dro.dur.ac.uk/next"})
    fetcher = Fetcher(transport=transport_that_returns([hop], []))

    answer = fetcher.fetch("https://dro.dur.ac.uk/aaa.pdf")

    assert isinstance(answer, Refused)
    assert answer.reason == reasons.FETCH_REFUSED
    assert answer.status == 0


def test_a_rate_limit_twice_raises_and_caches_nothing() -> None:
    calls: list = []
    limited = httpx.Response(429)
    fetcher = Fetcher(transport=transport_that_returns([limited], calls))

    with pytest.raises(FetchFailed):
        fetcher.fetch("https://dro.dur.ac.uk/aaa.pdf")

    assert len(calls) == 2
    key = cache.cache_key(
        "fetch",
        {
            "api": "open-copy-fetch",
            "url": "https://dro.dur.ac.uk/aaa.pdf",
            "redirects": 3,
            "max_bytes": MAX_BYTES,
            "shape": 1,
        },
    )
    assert cache.read(key) is None


def test_a_timeout_gets_one_retry_then_raises() -> None:
    calls: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        raise httpx.ConnectTimeout("too slow")

    fetcher = Fetcher(transport=httpx.MockTransport(handler))

    with pytest.raises(FetchFailed):
        fetcher.fetch("https://dro.dur.ac.uk/aaa.pdf")
    assert len(calls) == 2


def test_a_timeout_that_passes_on_the_retry_returns_the_pdf() -> None:
    calls: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ConnectTimeout("too slow")
        return pdf_response()

    fetcher = Fetcher(transport=httpx.MockTransport(handler))

    answer = fetcher.fetch("https://dro.dur.ac.uk/aaa.pdf")

    assert isinstance(answer, Fetched)
    assert len(calls) == 2


def test_two_links_on_one_host_wait_and_two_hosts_do_not(monkeypatch) -> None:
    waits: list = []
    monkeypatch.setattr("fynd.fetcher.time.sleep", lambda seconds: waits.append(seconds))
    # The clock stands still, so every wait is the full second.
    monkeypatch.setattr("fynd.fetcher.time.monotonic", lambda: 100.0)
    fetcher = Fetcher(transport=transport_that_returns([pdf_response()], []))

    fetcher.fetch("https://dro.dur.ac.uk/aaa.pdf")
    assert waits == []

    fetcher.fetch("https://dro.dur.ac.uk/bbb.pdf")
    assert waits == [1.0]

    fetcher.fetch("https://www.mdpi.com/ccc.pdf")
    assert waits == [1.0]


def test_the_request_names_fynd_and_the_operator() -> None:
    calls: list = []
    fetcher = Fetcher(transport=transport_that_returns([pdf_response()], calls))

    fetcher.fetch("https://dro.dur.ac.uk/aaa.pdf")

    agent = calls[0].headers["user-agent"]
    assert "Fynd" in agent
    assert "github.com/deshanekanayaka/Fynd" in agent
    assert "deshan@example.org" in agent


def test_a_missing_contact_email_stops_the_run(monkeypatch) -> None:
    monkeypatch.delenv("FYND_CONTACT_EMAIL", raising=False)
    calls: list = []

    with pytest.raises(ContactEmailMissing):
        Fetcher(transport=transport_that_returns([pdf_response()], calls))
    assert calls == []

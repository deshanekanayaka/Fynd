"""The fetcher has to obey every rule in ADR 0007, and cache what it learned."""

import httpx
import pytest

from fynd import cache, reasons
from fynd.contact import ContactEmailMissing
from fynd.fetcher import MAX_BYTES, Fetched, Fetcher, FetchFailed, Refused

PDF_BODY = b"%PDF-1.7 a short paper"


def transport_that_returns(
    responses: list,
    calls: list,
    robots: httpx.Response | None = None,
    robots_calls: list | None = None,
) -> httpx.MockTransport:
    """Builds a transport that answers each file request from the list in order.

    A request for `robots.txt` is answered apart, and it is not counted in
    `calls`, so a test about the file says what it means. The default answer
    is a 404, which allows everything under RFC 9309.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            if robots_calls is not None:
                robots_calls.append(request)
            return robots if robots is not None else httpx.Response(404)
        calls.append(request)
        index = min(len(calls) - 1, len(responses) - 1)
        return responses[index]

    return httpx.MockTransport(handler)


def pdf_response() -> httpx.Response:
    return httpx.Response(200, content=PDF_BODY, headers={"content-type": "application/pdf"})


PAPER_URL = "https://dro.dur.ac.uk/aaa.pdf"


def fetch(response: httpx.Response, url: str = PAPER_URL, calls: list | None = None):
    """Reads one file from a host that answers with the given response."""
    fetcher = Fetcher(
        transport=transport_that_returns([response], calls if calls is not None else [])
    )
    return fetcher.fetch(url)


def test_a_pdf_comes_back_as_bytes() -> None:
    answer = fetch(pdf_response())

    assert isinstance(answer, Fetched)
    assert answer.data == PDF_BODY
    assert answer.content_type == "application/pdf"


def test_a_second_fetch_makes_no_request() -> None:
    calls: list = []
    fetcher = Fetcher(transport=transport_that_returns([pdf_response()], calls))
    fetcher.fetch(PAPER_URL)
    fetcher.fetch(PAPER_URL)
    assert len(calls) == 1

    # A new run reads the same sidecar, which is what makes the measurement
    # reproducible with no network.
    second = Fetcher(transport=transport_that_returns([pdf_response()], []))
    answer = second.fetch(PAPER_URL)
    assert isinstance(answer, Fetched)


def test_pdf_bytes_with_a_wrong_content_type_are_accepted() -> None:
    page = httpx.Response(200, content=PDF_BODY, headers={"content-type": "text/html"})

    answer = fetch(page, url="https://pdpublishers.com/aaa")

    assert isinstance(answer, Fetched)


@pytest.mark.parametrize(
    ("response", "url", "reason", "status"),
    [
        # A login page named .pdf is caught by its first bytes, which are not %PDF.
        (
            httpx.Response(
                200, content=b"<html>Please sign in</html>", headers={"content-type": "text/html"}
            ),
            "https://www.sciencedirect.com/aaa.pdf",
            reasons.NOT_A_PDF,
            200,
        ),
        (
            httpx.Response(
                200,
                content=PDF_BODY + b"x" * (MAX_BYTES + 1),
                headers={"content-type": "application/pdf"},
            ),
            "https://dro.dur.ac.uk/big.pdf",
            reasons.FETCH_REFUSED,
            200,
        ),
        # The redirect limit is 3. A chain that never ends answers nothing, so
        # there is no final status to record.
        (
            httpx.Response(302, headers={"location": "https://dro.dur.ac.uk/next"}),
            PAPER_URL,
            reasons.FETCH_REFUSED,
            0,
        ),
    ],
    ids=["a login page", "a body over the cap", "a fourth redirect"],
)
def test_a_reply_that_is_not_a_usable_file_is_refused(
    response: httpx.Response, url: str, reason: str, status: int
) -> None:
    answer = fetch(response, url=url)

    assert isinstance(answer, Refused)
    assert answer.reason == reason
    assert answer.status == status


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


def test_a_rate_limit_twice_raises_and_caches_nothing() -> None:
    calls: list = []
    limited = httpx.Response(429)
    fetcher = Fetcher(transport=transport_that_returns([limited], calls))

    with pytest.raises(FetchFailed):
        fetcher.fetch(PAPER_URL)

    assert len(calls) == 2
    key = cache.cache_key(
        "fetch",
        {
            "api": "open-copy-fetch",
            "url": PAPER_URL,
            "redirects": 3,
            "max_bytes": MAX_BYTES,
            "shape": 1,
        },
    )
    assert cache.read(key) is None


def test_a_timeout_gets_one_retry_then_raises() -> None:
    calls: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        # The host answers its robots.txt and then times out on the file.
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        calls.append(request)
        raise httpx.ConnectTimeout("too slow")

    fetcher = Fetcher(transport=httpx.MockTransport(handler))

    with pytest.raises(FetchFailed):
        fetcher.fetch(PAPER_URL)
    assert len(calls) == 2


def test_a_timeout_that_passes_on_the_retry_returns_the_pdf() -> None:
    calls: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ConnectTimeout("too slow")
        return pdf_response()

    fetcher = Fetcher(transport=httpx.MockTransport(handler))

    answer = fetcher.fetch(PAPER_URL)

    assert isinstance(answer, Fetched)
    assert len(calls) == 2


def test_two_links_on_one_host_wait_and_two_hosts_do_not(monkeypatch) -> None:
    waits: list = []
    monkeypatch.setattr("fynd.fetcher.time.sleep", lambda seconds: waits.append(seconds))
    # The clock stands still, so every wait is the full second.
    monkeypatch.setattr("fynd.fetcher.time.monotonic", lambda: 100.0)
    fetcher = Fetcher(transport=transport_that_returns([pdf_response()], []))

    # The robots.txt of a host is a request to that host, so the file after it
    # waits the full second.
    fetcher.fetch("https://dro.dur.ac.uk/aaa.pdf")
    assert waits == [1.0]

    fetcher.fetch("https://dro.dur.ac.uk/bbb.pdf")
    assert waits == [1.0, 1.0]

    # A second host is read from its own robots.txt, so it waits once for
    # that request and not for the first host.
    fetcher.fetch("https://www.mdpi.com/ccc.pdf")
    assert waits == [1.0, 1.0, 1.0]


def test_the_request_names_fynd_and_the_operator() -> None:
    calls: list = []
    fetcher = Fetcher(transport=transport_that_returns([pdf_response()], calls))

    fetcher.fetch(PAPER_URL)

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

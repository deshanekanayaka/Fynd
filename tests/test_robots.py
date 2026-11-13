"""Fynd reads robots.txt before it fetches, and obeys it. See RFC 9309."""

import time

import httpx
import pytest

from fynd import reasons
from fynd.fetcher import (
    MAX_CRAWL_DELAY_SECONDS,
    ROBOTS_MAX_AGE_SECONDS,
    ROBOTS_MAX_BYTES,
    SECONDS_BETWEEN_REQUESTS,
    Fetched,
    Fetcher,
    Refused,
)

PDF_BODY = b"%PDF-1.7 a short paper"
PAPER_URL = "https://dro.dur.ac.uk/id/eprint/1/aaa.pdf"
SECOND_PAPER_URL = "https://dro.dur.ac.uk/id/eprint/2/bbb.pdf"

ALLOW_ALL = "User-agent: *\nDisallow:\n"
DISALLOW_THE_PAPERS = "User-agent: *\nDisallow: /id/eprint/\n"


def transport_with_robots(
    robots: httpx.Response, calls: list, robots_calls: list | None = None
) -> httpx.MockTransport:
    """Answers robots.txt with the given reply, and any file with a PDF."""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            if robots_calls is not None:
                robots_calls.append(request)
            return robots
        calls.append(request)
        return httpx.Response(200, content=PDF_BODY, headers={"content-type": "application/pdf"})

    return httpx.MockTransport(handler)


def robots_text(body: str, status: int = 200) -> httpx.Response:
    return httpx.Response(status, text=body, headers={"content-type": "text/plain"})


def fetcher_with(
    robots: httpx.Response, calls: list | None = None, robots_calls: list | None = None
) -> Fetcher:
    """Builds a fetcher for a host whose robots.txt answers in the given way."""
    return Fetcher(
        transport=transport_with_robots(robots, calls if calls is not None else [], robots_calls)
    )


def fetch_with(robots: httpx.Response, url: str = PAPER_URL, calls: list | None = None):
    """Reads one file from a host whose robots.txt answers in the given way."""
    return fetcher_with(robots, calls=calls).fetch(url)


@pytest.mark.parametrize(
    "robots",
    [
        robots_text("User-agent: *\nDisallow: /private/\n"),
        # A missing file allows everything under RFC 9309.
        httpx.Response(404),
        # A host that sends a megabyte at robots.txt is not sending rules, and
        # the body is cut at the cap rather than read as one long rule.
        robots_text("# comment\n" * (ROBOTS_MAX_BYTES // 5)),
    ],
    ids=["another path is disallowed", "no robots file", "a huge body"],
)
def test_a_file_is_fetched_when_robots_does_not_refuse_it(robots: httpx.Response) -> None:
    calls: list = []

    answer = fetch_with(robots, calls=calls)

    assert isinstance(answer, Fetched)
    assert answer.data == PDF_BODY
    assert len(calls) == 1


@pytest.mark.parametrize(
    "robots",
    [
        robots_text(DISALLOW_THE_PAPERS),
        # A 5xx says nothing about what is allowed, so this run asks for
        # nothing on that host. RFC 9309 names that rule.
        httpx.Response(500),
        # A host that names Fynd is naming this program.
        robots_text("User-agent: Fynd\nDisallow: /\n"),
        # 30 seconds for each file is 10 minutes over 20 Papers.
        robots_text(f"User-agent: *\nCrawl-delay: {int(MAX_CRAWL_DELAY_SECONDS) + 1}\n"),
    ],
    ids=["the path is disallowed", "a broken robots file", "fynd is named", "a long crawl delay"],
)
def test_a_file_is_never_fetched_when_robots_refuses_it(robots: httpx.Response) -> None:
    calls: list = []

    answer = fetch_with(robots, calls=calls)

    assert isinstance(answer, Refused)
    assert answer.reason == reasons.ROBOTS_REFUSED
    assert calls == []


def test_rules_written_for_another_program_do_not_apply() -> None:
    # A host that names another program is not naming Fynd. This is a second
    # host, because one robots answer is cached for each host.
    answer = fetch_with(
        robots_text("User-agent: SomeBot\nDisallow: /\n"),
        url="https://discovery.ucl.ac.uk/id/eprint/1/a.pdf",
    )

    assert isinstance(answer, Fetched)


@pytest.mark.parametrize(
    ("delay", "expected"),
    [
        (5, 5.0),
        # A host that asks for less than Fynd's own wait does not get it.
        (0, SECONDS_BETWEEN_REQUESTS),
    ],
)
def test_a_crawl_delay_sets_the_wait_for_that_host(delay: int, expected: float) -> None:
    fetcher = fetcher_with(robots_text(f"User-agent: *\nCrawl-delay: {delay}\nDisallow:\n"))

    fetcher.fetch(PAPER_URL)

    assert fetcher.wait_seconds_for("dro.dur.ac.uk") == expected


def test_the_robots_file_is_read_once_for_a_host() -> None:
    robots_calls: list = []
    fetcher = fetcher_with(robots_text(ALLOW_ALL), robots_calls=robots_calls)

    fetcher.fetch(PAPER_URL)
    fetcher.fetch(SECOND_PAPER_URL)

    assert len(robots_calls) == 1


def test_the_robots_file_is_cached_on_disk() -> None:
    fetch_with(robots_text(ALLOW_ALL))

    robots_calls: list = []
    second = fetcher_with(robots_text(ALLOW_ALL), robots_calls=robots_calls)
    second.fetch(SECOND_PAPER_URL)

    assert robots_calls == []


@pytest.mark.parametrize(
    "answer_once",
    [
        # One bad day at one university must not wall that host off for ever.
        httpx.Response(500),
        # A 429 says nothing about what a host permits. Stored, it would refuse
        # that host for ever, because nothing in the cache expires it.
        httpx.Response(429),
    ],
    ids=["a broken robots file", "a rate limit"],
)
def test_a_robots_answer_that_states_no_rules_is_not_cached(answer_once: httpx.Response) -> None:
    fetch_with(answer_once)

    answer = fetch_with(robots_text(ALLOW_ALL))

    assert isinstance(answer, Fetched)


def test_a_robots_refusal_writes_no_fetch_answer(a_cache_and_an_address) -> None:
    # The robots answer is cached on its own. A fetch refusal in the cache
    # would say a host refused a request that Fynd never sent.
    fetch_with(robots_text(DISALLOW_THE_PAPERS))

    written = [path.name for path in a_cache_and_an_address.iterdir()]

    assert [name for name in written if name.startswith("fetch-")] == []
    assert [name for name in written if name.startswith("robots-")] != []


def test_a_robots_redirect_loop_allows_nothing_and_does_not_crash() -> None:
    # httpx raises TooManyRedirects, which is not a transport error. Out of
    # the fetch it would end the whole measurement run on one Paper.
    calls: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(302, headers={"location": "/robots.txt?a=1"})
        calls.append(request)
        return httpx.Response(200, content=PDF_BODY)

    answer = Fetcher(transport=httpx.MockTransport(handler)).fetch(PAPER_URL)

    assert isinstance(answer, Refused)
    assert answer.reason == reasons.ROBOTS_REFUSED
    assert calls == []


def test_a_stored_robots_answer_is_read_again_after_a_day(monkeypatch) -> None:
    # A repository that adds a rule next week must win over a file Fynd read
    # today. RFC 9309 asks for one day at most.
    fetch_with(robots_text(ALLOW_ALL))

    a_day_later = time.time() + ROBOTS_MAX_AGE_SECONDS + 1
    monkeypatch.setattr("fynd.fetcher.time.time", lambda: a_day_later)
    robots_calls: list = []
    second = fetcher_with(robots_text(DISALLOW_THE_PAPERS), robots_calls=robots_calls)

    answer = second.fetch(PAPER_URL)

    assert len(robots_calls) == 1
    assert isinstance(answer, Refused)
    assert answer.reason == reasons.ROBOTS_REFUSED


def test_a_link_with_no_host_is_never_fetched() -> None:
    # Such a link would share one robots answer with every other one, and the
    # rules of one host must never govern another.
    calls: list = []

    answer = fetch_with(
        robots_text(ALLOW_ALL), url="dro.dur.ac.uk/id/eprint/1/aaa.pdf", calls=calls
    )

    assert isinstance(answer, Refused)
    assert answer.reason == reasons.FETCH_REFUSED
    assert calls == []

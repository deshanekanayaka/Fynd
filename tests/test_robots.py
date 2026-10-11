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


@pytest.fixture(autouse=True)
def a_cache_and_an_address(tmp_path, monkeypatch):
    """Gives every test its own cache directory and an operator address."""
    monkeypatch.setenv("FYND_CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("FYND_CONTACT_EMAIL", "deshan@example.org")
    monkeypatch.setattr("fynd.fetcher.time.sleep", lambda seconds: None)
    return tmp_path


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
        return httpx.Response(
            200, content=PDF_BODY, headers={"content-type": "application/pdf"}
        )

    return httpx.MockTransport(handler)


def robots_text(body: str, status: int = 200) -> httpx.Response:
    return httpx.Response(status, text=body, headers={"content-type": "text/plain"})


def test_a_disallowed_path_is_never_fetched() -> None:
    calls: list = []
    rules = robots_text("User-agent: *\nDisallow: /id/eprint/\n")
    fetcher = Fetcher(transport=transport_with_robots(rules, calls))

    answer = fetcher.fetch(PAPER_URL)

    assert isinstance(answer, Refused)
    assert answer.reason == reasons.ROBOTS_REFUSED
    assert calls == []


def test_an_allowed_path_is_fetched_as_before() -> None:
    calls: list = []
    rules = robots_text("User-agent: *\nDisallow: /private/\n")
    fetcher = Fetcher(transport=transport_with_robots(rules, calls))

    answer = fetcher.fetch(PAPER_URL)

    assert isinstance(answer, Fetched)
    assert answer.data == PDF_BODY
    assert len(calls) == 1


def test_a_missing_robots_file_allows_everything() -> None:
    calls: list = []
    fetcher = Fetcher(transport=transport_with_robots(httpx.Response(404), calls))

    answer = fetcher.fetch(PAPER_URL)

    assert isinstance(answer, Fetched)


def test_a_broken_robots_file_allows_nothing() -> None:
    # A 5xx says nothing about what is allowed, so this run asks for nothing
    # on that host. RFC 9309 names that rule.
    calls: list = []
    fetcher = Fetcher(transport=transport_with_robots(httpx.Response(500), calls))

    answer = fetcher.fetch(PAPER_URL)

    assert isinstance(answer, Refused)
    assert answer.reason == reasons.ROBOTS_REFUSED
    assert calls == []


def test_a_broken_robots_file_is_not_cached() -> None:
    # One bad day at one university must not wall that host off for ever.
    Fetcher(transport=transport_with_robots(httpx.Response(500), [])).fetch(PAPER_URL)

    calls: list = []
    rules = robots_text("User-agent: *\nDisallow:\n")
    answer = Fetcher(transport=transport_with_robots(rules, calls)).fetch(PAPER_URL)

    assert isinstance(answer, Fetched)


def test_the_robots_file_is_read_once_for_a_host() -> None:
    calls: list = []
    robots_calls: list = []
    rules = robots_text("User-agent: *\nDisallow:\n")
    fetcher = Fetcher(transport=transport_with_robots(rules, calls, robots_calls))

    fetcher.fetch(PAPER_URL)
    fetcher.fetch("https://dro.dur.ac.uk/id/eprint/2/bbb.pdf")

    assert len(robots_calls) == 1


def test_the_robots_file_is_cached_on_disk() -> None:
    rules = robots_text("User-agent: *\nDisallow:\n")
    Fetcher(transport=transport_with_robots(rules, [], [])).fetch(PAPER_URL)

    robots_calls: list = []
    second = Fetcher(transport=transport_with_robots(rules, [], robots_calls))
    second.fetch("https://dro.dur.ac.uk/id/eprint/2/bbb.pdf")

    assert robots_calls == []


def test_the_rules_are_matched_against_the_agent_fynd_sends() -> None:
    # A host that names Fynd is naming this program, and a host that names
    # another program is not. Two hosts, because one robots answer is cached
    # for each host.
    calls: list = []
    for_fynd = robots_text("User-agent: Fynd\nDisallow: /\n")
    answer = Fetcher(transport=transport_with_robots(for_fynd, calls)).fetch(PAPER_URL)
    assert isinstance(answer, Refused)
    assert answer.reason == reasons.ROBOTS_REFUSED
    assert calls == []

    other: list = []
    for_another = robots_text("User-agent: SomeBot\nDisallow: /\n")
    second = Fetcher(transport=transport_with_robots(for_another, other))
    assert isinstance(second.fetch("https://discovery.ucl.ac.uk/id/eprint/1/a.pdf"), Fetched)


def test_a_crawl_delay_sets_the_wait_for_that_host() -> None:
    calls: list = []
    rules = robots_text("User-agent: *\nCrawl-delay: 5\nDisallow:\n")
    fetcher = Fetcher(transport=transport_with_robots(rules, calls))

    fetcher.fetch(PAPER_URL)

    assert fetcher.wait_seconds_for("dro.dur.ac.uk") == 5.0


def test_a_small_crawl_delay_does_not_lower_the_wait() -> None:
    calls: list = []
    rules = robots_text("User-agent: *\nCrawl-delay: 0\nDisallow:\n")
    fetcher = Fetcher(transport=transport_with_robots(rules, calls))

    fetcher.fetch(PAPER_URL)

    assert fetcher.wait_seconds_for("dro.dur.ac.uk") == SECONDS_BETWEEN_REQUESTS


def test_a_long_crawl_delay_skips_the_host() -> None:
    # 30 seconds for each file is 10 minutes over 20 Papers.
    calls: list = []
    rules = robots_text(f"User-agent: *\nCrawl-delay: {int(MAX_CRAWL_DELAY_SECONDS) + 1}\n")
    fetcher = Fetcher(transport=transport_with_robots(rules, calls))

    answer = fetcher.fetch(PAPER_URL)

    assert isinstance(answer, Refused)
    assert answer.reason == reasons.ROBOTS_REFUSED
    assert calls == []


def test_a_robots_refusal_writes_no_fetch_answer(a_cache_and_an_address) -> None:
    # The robots answer is cached on its own. A fetch refusal in the cache
    # would say a host refused a request that Fynd never sent.
    rules = robots_text("User-agent: *\nDisallow: /id/eprint/\n")
    Fetcher(transport=transport_with_robots(rules, [])).fetch(PAPER_URL)

    written = [path.name for path in a_cache_and_an_address.iterdir()]

    assert [name for name in written if name.startswith("fetch-")] == []
    assert [name for name in written if name.startswith("robots-")] != []


def test_a_rate_limit_on_robots_is_not_cached() -> None:
    # A 429 says nothing about what a host permits. Stored, it would refuse
    # that host for ever, because nothing in the cache expires it.
    Fetcher(transport=transport_with_robots(httpx.Response(429), [])).fetch(PAPER_URL)

    calls: list = []
    allowed = robots_text("User-agent: *\nDisallow:\n")
    answer = Fetcher(transport=transport_with_robots(allowed, calls)).fetch(PAPER_URL)

    assert isinstance(answer, Fetched)


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
    rules = robots_text("User-agent: *\nDisallow:\n")
    Fetcher(transport=transport_with_robots(rules, [], [])).fetch(PAPER_URL)

    a_day_later = time.time() + ROBOTS_MAX_AGE_SECONDS + 1
    monkeypatch.setattr("fynd.fetcher.time.time", lambda: a_day_later)
    robots_calls: list = []
    disallow = robots_text("User-agent: *\nDisallow: /id/eprint/\n")
    second = Fetcher(transport=transport_with_robots(disallow, [], robots_calls))

    answer = second.fetch(PAPER_URL)

    assert len(robots_calls) == 1
    assert isinstance(answer, Refused)
    assert answer.reason == reasons.ROBOTS_REFUSED


def test_a_huge_robots_body_is_cut_at_the_cap() -> None:
    # A host that sends a megabyte at robots.txt is not sending rules.
    calls: list = []
    body = "# comment\n" * (ROBOTS_MAX_BYTES // 5)
    fetcher = Fetcher(transport=transport_with_robots(robots_text(body), calls))

    answer = fetcher.fetch(PAPER_URL)

    assert isinstance(answer, Fetched)


def test_a_link_with_no_host_is_never_fetched() -> None:
    # Such a link would share one robots answer with every other one, and the
    # rules of one host must never govern another.
    calls: list = []
    rules = robots_text("User-agent: *\nDisallow:\n")
    fetcher = Fetcher(transport=transport_with_robots(rules, calls))

    answer = fetcher.fetch("dro.dur.ac.uk/id/eprint/1/aaa.pdf")

    assert isinstance(answer, Refused)
    assert answer.reason == reasons.FETCH_REFUSED
    assert calls == []

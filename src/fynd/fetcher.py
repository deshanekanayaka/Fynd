"""Fetch one Open copy, under the rules in ADR 0007 and ADR 0012.

This file receives a link OpenAlex marked open, and a doi.org link never
reaches it, because that host holds no file.

Every link passes the robots.txt of its host first, under RFC 9309. The check
sits here, because every link reaches the network through this one method.

A host that returns no file is an answer and not a crash, so the fetch returns
`Fetched` or `Refused`. A rate limit and a timeout are a failure, they get one
retry, and then the fetch raises.
"""

import time
from dataclasses import dataclass
from typing import Final
from urllib import robotparser
from urllib.parse import urlparse, urlunsplit

import httpx

from fynd import cache, reasons
from fynd.contact import user_agent

# The rules of ADR 0007.
MAX_REDIRECTS: Final = 3
MAX_BYTES: Final = 20 * 1024 * 1024
TIMEOUT_SECONDS: Final = 30.0
SECONDS_BETWEEN_REQUESTS: Final = 1.0
RETRY_WAIT_SECONDS: Final = 3.0

# The first bytes of a PDF. A login page that arrives with a PDF name fails
# this check, and a PDF served as a stream of bytes passes it.
PDF_MAGIC: Final = b"%PDF"
PDF_CONTENT_TYPE: Final = "application/pdf"

RATE_LIMIT_STATUS: Final = 429

# A refusal with no final status. A redirect chain that never ends answers
# nothing, so there is no status to record.
NO_STATUS: Final = 0

# The shape of the stored answer. The cache key carries it.
FETCH_SHAPE_VERSION: Final = 1

# The robots.txt rules of RFC 9309. A 404, and any other 4xx but a rate
# limit, allows everything. A 5xx and a rate limit allow nothing on that host
# for this run, and neither answer is cached, so one bad day at one university
# does not wall that host off for ever.
ROBOTS_PATH: Final = "/robots.txt"
ROBOTS_SHAPE_VERSION: Final = 1

# A host may name a `Crawl-delay`. Fynd waits the larger of its own one second
# and that delay. A delay above this cap costs 10 minutes over 20 Papers, so
# the host is skipped instead.
MAX_CRAWL_DELAY_SECONDS: Final = 10.0


class FetchFailed(Exception):
    """Raised when a host refuses twice with a rate limit or a timeout."""


@dataclass(frozen=True)
class Fetched:
    """The bytes of one Open copy, with the content type the host sent."""

    data: bytes
    content_type: str


@dataclass(frozen=True)
class Refused:
    """A host that returned no file, with the reason the measurement counts."""

    status: int
    content_type: str
    reason: str


FetchAnswer = Fetched | Refused


@dataclass(frozen=True)
class Robots:
    """What one host allows this run, and how long to wait between requests."""

    # None with `refuse_all` false means every path is allowed, which is what
    # a host with no robots.txt says.
    rules: robotparser.RobotFileParser | None
    refuse_all: bool
    wait: float

    def allows(self, url: str, agent: str) -> bool:
        """Says whether this host allows one link for one user agent."""
        if self.refuse_all:
            return False
        if self.rules is None:
            return True
        return self.rules.can_fetch(agent, url)


def robots_url_of(url: str) -> str:
    """Returns the robots.txt address of the host one link sits on."""
    parts = urlparse(url)
    return urlunsplit((parts.scheme or "https", parts.netloc, ROBOTS_PATH, "", ""))


def robots_from(status: int, text: str, agent: str) -> Robots:
    """Turns one robots.txt answer into the rules Fynd obeys."""
    if status != 200:
        # Every 4xx but a rate limit allows everything. A 5xx and a rate limit
        # allow nothing, because neither says what this host permits.
        allowed = 400 <= status < 500 and status != RATE_LIMIT_STATUS
        return Robots(rules=None, refuse_all=not allowed, wait=SECONDS_BETWEEN_REQUESTS)

    rules = robotparser.RobotFileParser()
    rules.parse(text.splitlines())
    # One difference to know: `robotparser` reads a whole number delay and
    # ignores a fractional one, so `Crawl-delay: 0.5` reads as no delay, and
    # Fynd then waits its own one second, which is longer.
    named = rules.crawl_delay(agent)
    delay = float(named) if named is not None else 0.0
    if delay > MAX_CRAWL_DELAY_SECONDS:
        return Robots(rules=rules, refuse_all=True, wait=SECONDS_BETWEEN_REQUESTS)
    return Robots(
        rules=rules, refuse_all=False, wait=max(SECONDS_BETWEEN_REQUESTS, delay)
    )


def host_of(url: str) -> str:
    """Returns the host part of a link, for example `dro.dur.ac.uk`."""
    return urlparse(url).netloc


def looks_like_a_pdf(content_type: str, body: bytes) -> bool:
    """Says whether this answer is a PDF, by its content type or its first bytes."""
    if PDF_CONTENT_TYPE in content_type.lower():
        return True
    return body.startswith(PDF_MAGIC)


class Fetcher:
    """A fetch client for one run, holding the last request time for each host."""

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        # A test passes a transport, and the client stays Fynd's own, because
        # the redirect limit and the timeout are rules this file owns.
        self.client = httpx.Client(
            transport=transport,
            timeout=TIMEOUT_SECONDS,
            follow_redirects=True,
            max_redirects=MAX_REDIRECTS,
            headers={"User-Agent": user_agent()},
        )
        self.last_request_at: dict[str, float] = {}
        # The robots.txt of each host, read once for a run.
        self.robots: dict[str, Robots] = {}

    def wait_seconds_for(self, host: str) -> float:
        """Returns the wait this host asks for, which is one second by default."""
        known = self.robots.get(host)
        return known.wait if known is not None else SECONDS_BETWEEN_REQUESTS

    def wait_for_host(self, host: str) -> None:
        """Waits until this host's wait has passed since the last request to it."""
        started = self.last_request_at.get(host)
        if started is None:
            return
        remaining = self.wait_seconds_for(host) - (time.monotonic() - started)
        if remaining > 0:
            time.sleep(remaining)

    def robots_for(self, url: str) -> Robots:
        """Returns the robots.txt rules of the host one link sits on.

        The answer is read once for a host in a run, and a 200 and a 4xx are
        cached on disk. A 5xx, a rate limit and a timeout are not cached.
        """
        host = host_of(url)
        known = self.robots.get(host)
        if known is not None:
            return known

        agent = user_agent()
        parts = {"api": "robots", "host": host, "shape": ROBOTS_SHAPE_VERSION}
        key = cache.cache_key("robots", parts)
        stored = cache.read(key)
        if stored is not None:
            answer = robots_from(int(stored["status"]), str(stored["text"]), agent)
            self.robots[host] = answer
            return answer

        status, text, answered = self.fetch_robots(url, host)
        answer = robots_from(status, text, agent)
        if answered:
            cache.write(key, parts, {"status": status, "text": text})
        self.robots[host] = answer
        return answer

    def fetch_robots(self, url: str, host: str) -> tuple[int, str, bool]:
        """Calls one host for its robots.txt. One of two methods that use the network.

        The third value says whether the host answered at all. A host that did
        not answer is asked again on the next run.
        """
        self.wait_for_host(host)
        try:
            response = self.client.get(robots_url_of(url))
        except (httpx.TimeoutException, httpx.TransportError):
            # No answer is not a permission. This run asks this host for
            # nothing, and nothing is cached.
            self.last_request_at[host] = time.monotonic()
            return 0, "", False
        self.last_request_at[host] = time.monotonic()
        if response.status_code == 200:
            return 200, response.text, True
        answered = 400 <= response.status_code < 500
        return response.status_code, "", answered

    def fetch(self, url: str) -> FetchAnswer:
        """Returns the bytes of one Open copy, or the reason a host gave none.

        The answer comes from the cache when it is there. Raises FetchFailed
        when the host answers with a rate limit or a timeout twice.

        robots.txt is read before the cache, so a path a host disallows is
        refused even when an earlier run already holds its bytes. A published
        table must not count a file Fynd may no longer ask for.
        """
        robots = self.robots_for(url)
        if not robots.allows(url, user_agent()):
            # Nothing is written to the fetch cache. The robots answer is
            # cached on its own, and a rule the host changes must win.
            return Refused(status=NO_STATUS, content_type="", reason=reasons.ROBOTS_REFUSED)

        parts = {
            "api": "open-copy-fetch",
            "url": url,
            "redirects": MAX_REDIRECTS,
            "max_bytes": MAX_BYTES,
            "shape": FETCH_SHAPE_VERSION,
        }
        key = cache.cache_key("fetch", parts)

        stored_bytes = cache.read_bytes(key)
        if stored_bytes is not None:
            return Fetched(data=stored_bytes.data, content_type=stored_bytes.content_type)

        stored = cache.read(key)
        if cache.is_refusal(stored):
            return Refused(
                status=int(stored["status"]),
                content_type=str(stored["content_type"]),
                reason=str(stored.get("reason") or reasons.FETCH_REFUSED),
            )

        answer = self.fetch_body(url)
        if isinstance(answer, Fetched):
            cache.write_bytes(key, parts, answer.data, answer.content_type)
        else:
            cache.write_refusal(
                key,
                parts,
                status=answer.status,
                content_type=answer.content_type,
                reason=answer.reason,
            )
        return answer

    def fetch_body(self, url: str) -> FetchAnswer:
        """Calls the host. The only method here that uses the network."""
        host = host_of(url)

        # Two tries at most. Nothing is cached on a failure, so a second ask
        # costs one wait.
        for attempt in (1, 2):
            self.wait_for_host(host)
            try:
                answer = self.read_one_response(url)
            except httpx.TooManyRedirects:
                # A chain that never ends is a host behaviour, and the table
                # counts it. There is no final status to record.
                self.last_request_at[host] = time.monotonic()
                return Refused(
                    status=NO_STATUS, content_type="", reason=reasons.FETCH_REFUSED
                )
            except (httpx.TimeoutException, httpx.TransportError):
                self.last_request_at[host] = time.monotonic()
                if attempt == 2:
                    raise FetchFailed(
                        f"The host {host} did not answer twice in a row. Nothing is "
                        "cached, so the same link is tried again when you ask again."
                    ) from None
                time.sleep(RETRY_WAIT_SECONDS)
                continue

            self.last_request_at[host] = time.monotonic()
            if answer is not None:
                return answer
            # A rate limit. The same two tries apply.
            if attempt == 2:
                raise FetchFailed(
                    f"The host {host} answered {RATE_LIMIT_STATUS} twice in a row. "
                    "Nothing is cached, so the same link is tried again later."
                )
            time.sleep(RETRY_WAIT_SECONDS)
        raise AssertionError("unreachable")

    def read_one_response(self, url: str) -> FetchAnswer | None:
        """Returns one answer, or None when the host sent a rate limit."""
        with self.client.stream("GET", url) as response:
            content_type = response.headers.get("content-type", "")
            if response.status_code == RATE_LIMIT_STATUS:
                return None
            if response.status_code != 200:
                return Refused(
                    status=response.status_code,
                    content_type=content_type,
                    reason=reasons.FETCH_REFUSED,
                )

            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > MAX_BYTES:
                    # A body over the cap is refused, and the bytes already read
                    # are dropped. The per Paper list shows the status and the
                    # content type, so a reader sees what happened.
                    return Refused(
                        status=response.status_code,
                        content_type=content_type,
                        reason=reasons.FETCH_REFUSED,
                    )

            data = bytes(body)
            if not looks_like_a_pdf(content_type, data):
                return Refused(
                    status=response.status_code,
                    content_type=content_type,
                    reason=reasons.NOT_A_PDF,
                )
            return Fetched(data=data, content_type=content_type or PDF_CONTENT_TYPE)

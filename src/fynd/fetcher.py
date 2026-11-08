"""Downloads candidate PDF files for the Open copy pipeline.

The pipeline supplies a URL. This client checks its host's robots.txt, reuses
cached bytes or refusals, and otherwise downloads with size and retry limits.
It returns Fetched or Refused; repeated temporary download failures raise
FetchFailed. PDF parsing and Source text checks happen in other files.
"""

import time
from dataclasses import dataclass
from typing import Final
from urllib import robotparser
from urllib.parse import urlparse, urlunsplit

import httpx

from fynd import cache, reasons
from fynd.contact import user_agent

# Bound redirects and response size so one candidate cannot consume unlimited work.
MAX_REDIRECTS: Final = 3
MAX_BYTES: Final = 20 * 1024 * 1024
# Configure HTTPX's network timeout; this is not a total Stage deadline.
TIMEOUT_SECONDS: Final = 30.0
SECONDS_BETWEEN_REQUESTS: Final = 1.0
RETRY_WAIT_SECONDS: Final = 3.0

# A signature accepts PDFs even when the host sends a generic content type.
PDF_MAGIC: Final = b"%PDF"
PDF_CONTENT_TYPE: Final = "application/pdf"

RATE_LIMIT_STATUS: Final = 429

# Use 0 when no final HTTP status exists, such as a redirect-limit refusal.
NO_STATUS: Final = 0

# Bump when stored fetch results change shape so old entries are not reused.
FETCH_SHAPE_VERSION: Final = 1

ROBOTS_PATH: Final = "/robots.txt"
ROBOTS_SHAPE_VERSION: Final = 2

# Refresh disk-cached rules after 24 hours so host policy changes can take effect.
ROBOTS_MAX_AGE_SECONDS: Final = 24 * 60 * 60

# Read at most 500 KiB of robots rules instead of accepting an unbounded response.
ROBOTS_MAX_BYTES: Final = 500 * 1024

# Skip hosts asking for more than 10 seconds between requests to bound waiting.
MAX_CRAWL_DELAY_SECONDS: Final = 10.0


class FetchFailed(Exception):
    """Raised after two download attempts end in rate limits or transport failures."""


@dataclass(frozen=True)
class Fetched:
    """Downloaded bytes accepted as a PDF, with their content type."""

    data: bytes
    content_type: str


@dataclass(frozen=True)
class Refused:
    """A rejected download with its status, content type, and reason."""

    status: int
    content_type: str
    reason: str


FetchAnswer = Fetched | Refused


@dataclass(frozen=True)
class Robots:
    """A host's robots rules, refusal flag, and request delay."""

    # No parser plus refuse_all=False represents unrestricted access.
    rules: robotparser.RobotFileParser | None
    refuse_all: bool
    wait: float

    def allows(self, url: str, agent: str) -> bool:
        """Checks whether the rules allow this URL for Fynd's User-Agent."""
        if self.refuse_all:
            return False
        if self.rules is None:
            return True
        return self.rules.can_fetch(agent, url)


def robots_url_of(url: str) -> str:
    """Builds the robots.txt URL for a download's scheme and host."""
    parts = urlparse(url)
    return urlunsplit((parts.scheme, parts.netloc, ROBOTS_PATH, "", ""))


def is_fetchable(url: str) -> bool:
    """Checks for an HTTP or HTTPS URL with a host."""
    parts = urlparse(url)
    return parts.scheme in ("http", "https") and bool(parts.netloc)


def robots_from(status: int, text: str, agent: str) -> Robots:
    """Turns one robots.txt answer into the rules Fynd obeys."""
    if status != 200:
        # A 4xx except 429 permits access; other statuses leave permission unknown.
        allowed = 400 <= status < 500 and status != RATE_LIMIT_STATUS
        return Robots(rules=None, refuse_all=not allowed, wait=SECONDS_BETWEEN_REQUESTS)

    rules = robotparser.RobotFileParser()
    rules.parse(text.splitlines())
    # The parser ignores fractional delays; the 1-second minimum still applies.
    named = rules.crawl_delay(agent)
    delay = float(named) if named is not None else 0.0
    if delay > MAX_CRAWL_DELAY_SECONDS:
        return Robots(rules=rules, refuse_all=True, wait=SECONDS_BETWEEN_REQUESTS)
    return Robots(rules=rules, refuse_all=False, wait=max(SECONDS_BETWEEN_REQUESTS, delay))


def host_of(url: str) -> str:
    """Returns the host part of a link, for example `dro.dur.ac.uk`."""
    return urlparse(url).netloc


def looks_like_a_pdf(content_type: str, body: bytes) -> bool:
    """Checks for a PDF content type or %PDF signature."""
    # This is an initial format check; extraction must still be able to parse it.
    if PDF_CONTENT_TYPE in content_type.lower():
        return True
    return body.startswith(PDF_MAGIC)


class Fetcher:
    """A PDF download client with per-host timing and cached robots rules."""

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        # Tests replace the transport while retaining timeout and redirect settings.
        self.client = httpx.Client(
            transport=transport,
            timeout=TIMEOUT_SECONDS,
            follow_redirects=True,
            max_redirects=MAX_REDIRECTS,
            headers={"User-Agent": user_agent()},
        )
        self.last_request_at: dict[str, float] = {}
        # Reuse each host's rules for this client instance.
        self.robots: dict[str, Robots] = {}

    def wait_seconds_for(self, host: str) -> float:
        """Returns the host's request delay, defaulting to 1 second."""
        known = self.robots.get(host)
        return known.wait if known is not None else SECONDS_BETWEEN_REQUESTS

    def wait_for_host(self, host: str) -> None:
        """Waits out the remaining delay after this host's last response."""
        # Use a 1-second minimum, or an accepted Crawl-delay up to 10 seconds.
        started = self.last_request_at.get(host)
        if started is None:
            return
        remaining = self.wait_seconds_for(host) - (time.monotonic() - started)
        if remaining > 0:
            time.sleep(remaining)

    def robots_for(self, url: str) -> Robots:
        """Returns robots rules from memory, a fresh disk entry, or a request."""
        parts = urlparse(url)
        host = parts.netloc
        known = self.robots.get(host)
        if known is not None:
            return known

        agent = user_agent()
        # Disk entries distinguish HTTP from HTTPS because permissions can differ.
        stored_parts = {
            "api": "robots",
            "scheme": parts.scheme,
            "host": host,
            "shape": ROBOTS_SHAPE_VERSION,
        }
        key = cache.cache_key("robots", stored_parts)
        stored = cache.read(key)
        if stored is not None and not self.robots_is_stale(stored):
            answer = robots_from(int(stored["status"]), str(stored["text"]), agent)
            self.robots[host] = answer
            return answer

        status, text, answered = self.fetch_robots(url, host)
        answer = robots_from(status, text, agent)
        if answered:
            cache.write(key, stored_parts, {"status": status, "text": text, "read_at": time.time()})
        self.robots[host] = answer
        return answer

    def robots_is_stale(self, stored: dict) -> bool:
        """Checks whether disk-cached robots rules are older than 24 hours."""
        read_at = float(stored.get("read_at") or 0.0)
        return time.time() - read_at > ROBOTS_MAX_AGE_SECONDS

    def fetch_robots(self, url: str, host: str) -> tuple[int, str, bool]:
        """Requests robots status and text, plus whether the reply may be cached."""
        self.wait_for_host(host)
        try:
            with self.client.stream("GET", robots_url_of(url)) as response:
                status = response.status_code
                text = ""
                if status == 200:
                    # Stop after 500 KiB of rules to bound memory use.
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) >= ROBOTS_MAX_BYTES:
                            break
                    text = bytes(body[:ROBOTS_MAX_BYTES]).decode("utf-8", "replace")
        except (httpx.TimeoutException, httpx.TooManyRedirects, httpx.TransportError):
            # Unknown permissions refuse access for this run without a disk entry.
            self.last_request_at[host] = time.monotonic()
            return 0, "", False
        self.last_request_at[host] = time.monotonic()
        if status == 200:
            return 200, text, True
        # Do not persist 429 or server failures as a lasting access decision.
        answered = 400 <= status < 500 and status != RATE_LIMIT_STATUS
        return status, "", answered

    def fetch(self, url: str) -> FetchAnswer:
        """Checks access, then returns cached or downloaded PDF bytes or a refusal."""
        if not is_fetchable(url):
            # Reject invalid targets before looking up permissions or using the cache.
            return Refused(status=NO_STATUS, content_type="", reason=reasons.FETCH_REFUSED)

        # Stored file bytes must not override the applicable robots permission.
        robots = self.robots_for(url)
        if not robots.allows(url, user_agent()):
            # Keep policy refusals out of the file cache; robots rules have their own cache.
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
        """Attempts a download twice at most, retrying temporary failures."""
        host = host_of(url)

        # One retry only; repeated failures raise without becoming cached refusals.
        for attempt in (1, 2):
            self.wait_for_host(host)
            try:
                answer = self.read_one_response(url)
            except httpx.TooManyRedirects:
                # More than 3 redirects is a recorded refusal, not another retry.
                self.last_request_at[host] = time.monotonic()
                return Refused(status=NO_STATUS, content_type="", reason=reasons.FETCH_REFUSED)
            except (httpx.TimeoutException, httpx.TransportError):
                self.last_request_at[host] = time.monotonic()
                if attempt == 2:
                    raise FetchFailed(
                        f"The host {host} did not answer twice in a row. Nothing is "
                        "cached, so the same link is tried again when you ask again."
                    ) from None
                # Wait 3 seconds before retrying a timeout or connection failure.
                time.sleep(RETRY_WAIT_SECONDS)
                continue

            self.last_request_at[host] = time.monotonic()
            if answer is not None:
                return answer
            # None means HTTP 429; it shares the same single-retry budget.
            if attempt == 2:
                raise FetchFailed(
                    f"The host {host} answered {RATE_LIMIT_STATUS} twice in a row. "
                    "Nothing is cached, so the same link is tried again later."
                )
            # Wait 3 seconds before retrying the rate-limited download.
            time.sleep(RETRY_WAIT_SECONDS)
        raise AssertionError("unreachable")

    def read_one_response(self, url: str) -> FetchAnswer | None:
        """Streams one response, returning None for HTTP 429."""
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
                    # Refuse downloads over 20 MiB instead of caching a partial file.
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

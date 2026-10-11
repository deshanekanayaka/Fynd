"""Fetch one Open copy, under the rules in ADR 0007.

Fynd never fetches a publisher. A doi.org link is a lookup key, and this file
receives only the repository link that OpenAlex resolved.

A host that returns no file is an answer and not a crash, so the fetch returns
`Fetched` or `Refused`. A rate limit and a timeout are a failure, they get one
retry, and then the fetch raises.
"""

import time
from dataclasses import dataclass
from typing import Final
from urllib.parse import urlparse

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

    def wait_for_host(self, host: str) -> None:
        """Waits until one second has passed since the last request to this host."""
        started = self.last_request_at.get(host)
        if started is None:
            return
        remaining = SECONDS_BETWEEN_REQUESTS - (time.monotonic() - started)
        if remaining > 0:
            time.sleep(remaining)

    def fetch(self, url: str) -> FetchAnswer:
        """Returns the bytes of one Open copy, or the reason a host gave none.

        The answer comes from the cache when it is there. Raises FetchFailed
        when the host answers with a rate limit or a timeout twice.
        """
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

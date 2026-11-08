"""Saves API replies, downloaded files, and fetch refusals on disk for reuse.

The Semantic Scholar, OpenAlex, Claude, and Voyage clients use JSON entries.
The fetcher stores file bytes beside JSON metadata; extraction caches derived
text. Callers check this cache before repeating a request or extraction.

Each entry records the inputs that identify its answer (ADR 0004). Tests and
CI can replay only the cached data available to them, not every local fetch.
"""

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

CACHE_DIR_VARIABLE: Final = "FYND_CACHE_DIR"
DEFAULT_CACHE_DIR: Final = ".cache"

# Tags distinguish file metadata and refusals from ordinary JSON replies.
BYTES_KIND: Final = "bytes"
REFUSAL_KIND: Final = "refusal"

# A rate limit is temporary; caching it would prevent a later request.
UNCACHEABLE_STATUS: Final = 429


@dataclass(frozen=True)
class CachedBytes:
    """The bytes of one fetch, with the content type the host sent."""

    data: bytes
    content_type: str


def cache_dir() -> Path:
    """Returns the configured cache directory, creating it when needed."""
    directory = Path(os.environ.get(CACHE_DIR_VARIABLE, DEFAULT_CACHE_DIR))
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def cache_key(name: str, parts: dict[str, Any]) -> str:
    """Builds a cache filename from a caller's name and request details."""
    # Sorted keys give identical inputs the same hash regardless of field order.
    text = json.dumps(parts, sort_keys=True)
    # Hashing keeps queries and URLs out of filenames; the name identifies the caller.
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{name}-{digest}.json"


def read_file(path: Path) -> Any | None:
    """Reads a JSON file, returning None for missing or malformed JSON."""
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        # Interrupted writes can leave partial JSON; treat it as a cache miss.
        return None


def read(key: str) -> Any | None:
    """Returns an entry's value, or None when the entry cannot be used."""
    stored = read_file(cache_dir() / key)
    if not isinstance(stored, dict) or "value" not in stored:
        # Older cache formats may not contain the expected value field.
        return None
    return stored["value"]


def write(key: str, parts: dict[str, Any], value: Any) -> None:
    """Stores a JSON value alongside the inputs that identify it."""
    # Keep the inputs so a reader can trace an answer to its request or model.
    path = cache_dir() / key
    path.write_text(json.dumps({"parts": parts, "value": value}, indent=2), encoding="utf-8")


def bytes_path(key: str) -> Path:
    """Returns the companion .bin path for a cache entry."""
    # Binary downloads stay separate because JSON cannot store bytes directly.
    return cache_dir() / f"{Path(key).stem}.bin"


def write_bytes(key: str, parts: dict[str, Any], data: bytes, content_type: str) -> None:
    """Stores downloaded bytes and their JSON metadata."""
    path = bytes_path(key)
    path.write_bytes(data)
    value = {
        "kind": BYTES_KIND,
        "content_type": content_type,
        "byte_count": len(data),
        "file": path.name,
    }
    # On a new entry, writing bytes first avoids metadata pointing to an absent file.
    write(key, parts, value)


def read_bytes(key: str) -> CachedBytes | None:
    """Returns stored bytes and content type, or None for an unusable entry."""
    value = read(key)
    if not isinstance(value, dict) or value.get("kind") != BYTES_KIND:
        return None
    path = cache_dir() / str(value.get("file") or "")
    if not path.is_file():
        # Metadata alone cannot restore a missing download.
        return None
    data = path.read_bytes()
    if len(data) != value.get("byte_count"):
        # Truncated downloads must not become input to Source text extraction.
        return None
    return CachedBytes(data=data, content_type=str(value.get("content_type") or ""))


def write_refusal(
    key: str, parts: dict[str, Any], status: int, content_type: str, reason: str = ""
) -> None:
    """Stores a fetch refusal, rejecting HTTP 429 rate limits."""
    # Enforce this here so callers cannot accidentally cache a rate-limit refusal.
    if status == UNCACHEABLE_STATUS:
        raise ValueError(
            f"A status of {UNCACHEABLE_STATUS} is a rate limit and never a cached answer. "
            "Wait and ask again, and cache nothing."
        )
    # The status alone cannot distinguish every refusal reason.
    write(
        key,
        parts,
        {
            "kind": REFUSAL_KIND,
            "status": status,
            "content_type": content_type,
            "reason": reason,
        },
    )


def is_refusal(value: Any) -> bool:
    """Checks whether a cached value represents a fetch refusal."""
    return isinstance(value, dict) and value.get("kind") == REFUSAL_KIND


def sha256_of(data: bytes) -> str:
    """Returns a SHA-256 hash identifying the supplied bytes."""
    return hashlib.sha256(data).hexdigest()


def read_parts(key: str) -> dict[str, Any]:
    """Returns an entry's recorded inputs, or an empty dictionary."""
    stored = read_file(cache_dir() / key)
    parts = stored.get("parts") if isinstance(stored, dict) else None
    return parts if isinstance(parts, dict) else {}

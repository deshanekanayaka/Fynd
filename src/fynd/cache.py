"""A cache on disk for every external call.

ADR 0004 makes this the foundation of the evaluation harness. A whole Project
replays from disk, so the tests repeat and continuous integration needs no key.
"""

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

CACHE_DIR_VARIABLE: Final = "FYND_CACHE_DIR"
DEFAULT_CACHE_DIR: Final = ".cache"

# The two stored shapes that are not a plain answer. The kind travels inside
# the value, so one read tells a caller which of the three it holds.
BYTES_KIND: Final = "bytes"
REFUSAL_KIND: Final = "refusal"

# A status Fynd never caches. A 429 is the rate limit, which one wait fixes,
# and a 403 or a 404 is a stable answer about a host. See ADR 0004.
UNCACHEABLE_STATUS: Final = 429


@dataclass(frozen=True)
class CachedBytes:
    """The bytes of one fetch, with the content type the host sent."""

    data: bytes
    content_type: str


def cache_dir() -> Path:
    """Returns the cache directory, and creates it if it is missing."""
    directory = Path(os.environ.get(CACHE_DIR_VARIABLE, DEFAULT_CACHE_DIR))
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def cache_key(name: str, parts: dict[str, Any]) -> str:
    """Builds the file name for one call from the values that change its answer."""
    # The name keeps the directory readable. The hash covers the parts, because
    # a query holds any character and a file name cannot. sort_keys makes the
    # same parts give the same key whatever order the caller wrote them in.
    text = json.dumps(parts, sort_keys=True)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{name}-{digest}.json"


def read(key: str) -> Any | None:
    """Returns the cached answer for this key, or None when there is none."""
    path = cache_dir() / key
    if not path.exists():
        return None
    stored = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(stored, dict) or "value" not in stored:
        # A file from an older shape, or a run that died inside the write. A
        # miss costs one fetch, and a raised error costs the whole Stage.
        return None
    return stored["value"]


def write(key: str, parts: dict[str, Any], value: Any) -> None:
    """Stores one answer with the parts that produced it.

    The parts are stored so a human reading the directory can tell which model
    and which prompt produced which reply. No caller writes a failed answer.
    """
    path = cache_dir() / key
    path.write_text(json.dumps({"parts": parts, "value": value}, indent=2), encoding="utf-8")


def bytes_path(key: str) -> Path:
    """Returns the sidecar file that holds the bytes for this key."""
    # The JSON file keeps the parts a human reads. The bytes sit beside it under
    # the same stem, because a 20 megabyte body is no JSON value.
    return cache_dir() / f"{Path(key).stem}.bin"


def write_bytes(key: str, parts: dict[str, Any], data: bytes, content_type: str) -> None:
    """Stores the bytes of one fetch in a sidecar file, with the parts beside it."""
    path = bytes_path(key)
    path.write_bytes(data)
    value = {
        "kind": BYTES_KIND,
        "content_type": content_type,
        "byte_count": len(data),
        "file": path.name,
    }
    # The bytes are written first, so a run that dies between the two writes
    # leaves no JSON file that promises a sidecar which is not there.
    write(key, parts, value)


def read_bytes(key: str) -> CachedBytes | None:
    """Returns the cached bytes for this key, or None when there are none."""
    value = read(key)
    if not isinstance(value, dict) or value.get("kind") != BYTES_KIND:
        return None
    path = cache_dir() / str(value.get("file") or "")
    if not path.is_file():
        # A run that died inside the write, or a sidecar a human deleted. A
        # miss costs one fetch.
        return None
    return CachedBytes(data=path.read_bytes(), content_type=str(value.get("content_type") or ""))


def write_refusal(
    key: str, parts: dict[str, Any], status: int, content_type: str, reason: str = ""
) -> None:
    """Stores the answer of a host that returned no file.

    Raises ValueError when the status is one that must never be cached.
    """
    # The rule lives here, because every caller of the cache passes through
    # this function and a guard in each caller is a guard someone forgets.
    if status == UNCACHEABLE_STATUS:
        raise ValueError(
            f"A status of {UNCACHEABLE_STATUS} is a rate limit and never a cached answer. "
            "Wait and ask again, and cache nothing."
        )
    # The reason is stored and never recomputed on a read. One status covers
    # several refusals, so a rule that reads the status back guesses.
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
    """Says whether a cached value is a host that returned no file."""
    return isinstance(value, dict) and value.get("kind") == REFUSAL_KIND

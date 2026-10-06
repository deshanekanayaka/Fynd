"""A cache on disk for every external fetch.

The PRD requires this from the first run, for two reasons. Semantic Scholar
allows one request per second, so a repeated run without a cache is slow. A
test also needs the same answer every time, and a cached file gives it.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any


def cache_dir() -> Path:
    """Return the directory the cache writes into, and create it if it is missing."""
    directory = Path(os.environ.get("FYND_CACHE_DIR", ".cache"))
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def cache_key(name: str, parts: dict[str, Any]) -> str:
    """Build the file name for one cached fetch.

    The name says what kind of fetch it was, so a human can read the directory.
    The hash covers the parameters, because a query can hold any character and
    a file name cannot.
    """
    # sort_keys makes the same parameters produce the same key every time.
    text = json.dumps(parts, sort_keys=True)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{name}-{digest}.json"


def read(key: str) -> Any | None:
    """Return the cached value for this key, or None when nothing is cached."""
    path = cache_dir() / key
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write(key: str, value: Any) -> None:
    """Store a value under this key."""
    path = cache_dir() / key
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")

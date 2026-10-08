"""A cache on disk for every external call.

ADR 0004 makes this the foundation of the evaluation harness and not an
optimization. A whole Project replays from disk with no network and no spend,
so the regression tests are repeatable and continuous integration needs no key.

The key holds every value that changes the answer. The file also stores those
values beside the answer, so a human reading the directory can tell which model
and which prompt produced which reply.
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
    """Build the file name for one cached call.

    The name says what kind of call it was, so a human can read the directory.
    The hash covers the parts, because a query holds any character and a file
    name cannot. sort_keys makes the same parts produce the same key every time.
    """
    text = json.dumps(parts, sort_keys=True)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{name}-{digest}.json"


def read(key: str) -> Any | None:
    """Return the cached answer for this key, or None when nothing is cached."""
    path = cache_dir() / key
    if not path.exists():
        return None
    stored = json.loads(path.read_text(encoding="utf-8"))
    return stored["value"]


def write(key: str, parts: dict[str, Any], value: Any) -> None:
    """Store one answer with the parts that produced it.

    A failed call is never cached. The caller decides what a failure is, and no
    caller writes one here. See ADR 0004.
    """
    path = cache_dir() / key
    stored = {"parts": parts, "value": value}
    path.write_text(json.dumps(stored, indent=2), encoding="utf-8")

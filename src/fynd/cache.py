"""A cache on disk for every external call.

ADR 0004 makes this the foundation of the evaluation harness. A whole Project
replays from disk, so the tests repeat and continuous integration needs no key.
"""

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Final

CACHE_DIR_VARIABLE: Final = "FYND_CACHE_DIR"
DEFAULT_CACHE_DIR: Final = ".cache"


def cache_dir() -> Path:
    """Return the cache directory, and create it if it is missing."""
    directory = Path(os.environ.get(CACHE_DIR_VARIABLE, DEFAULT_CACHE_DIR))
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def cache_key(name: str, parts: dict[str, Any]) -> str:
    """Build the file name for one call from the values that change its answer."""
    # The name keeps the directory readable. The hash covers the parts, because
    # a query holds any character and a file name cannot. sort_keys makes the
    # same parts give the same key whatever order the caller wrote them in.
    text = json.dumps(parts, sort_keys=True)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"{name}-{digest}.json"


def read(key: str) -> Any | None:
    """Return the cached answer for this key, or None when there is none."""
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
    """Store one answer with the parts that produced it.

    The parts are stored so a human reading the directory can tell which model
    and which prompt produced which reply. No caller writes a failed answer.
    """
    path = cache_dir() / key
    path.write_text(json.dumps({"parts": parts, "value": value}, indent=2), encoding="utf-8")

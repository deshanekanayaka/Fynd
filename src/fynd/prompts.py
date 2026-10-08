"""Every prompt is a file on disk, and never a string inside Python.

ADR 0004 asks for two things. A reader finds the prompt by its version in the
file name, and the cache key holds the hash of the file content. A typo fixed
without a rename still misses the cache, so no published number belongs to a
prompt that no longer exists.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Prompt:
    """One prompt file, with the hash the cache key needs."""

    name: str
    text: str
    sha256: str


def prompts_dir() -> Path:
    """Return the directory that holds the prompt files.

    The default is the `prompts` directory of the repository. A test points the
    environment variable at its own directory, so a test never depends on the
    wording of a real prompt.
    """
    from_environment = os.environ.get("FYND_PROMPTS_DIR")
    if from_environment:
        return Path(from_environment)
    # This file is src/fynd/prompts.py, so two levels up is the repository.
    return Path(__file__).resolve().parents[2] / "prompts"


def load(name: str) -> Prompt:
    """Read one prompt file and hash its content.

    The hash covers the whole file, so any edit changes the cache key. See
    ADR 0004.
    """
    path = prompts_dir() / f"{name}.md"
    text = path.read_text(encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return Prompt(name=name, text=text, sha256=digest)


def fill(prompt: Prompt, values: dict[str, str]) -> str:
    """Replace every placeholder in the prompt text.

    A placeholder is an upper case name inside double braces, for example
    {{DOMAIN_NAME}}. The braces matter: without them the name DOMAIN would
    replace the first half of DOMAIN_NAME and leave the rest behind.
    """
    filled = prompt.text
    for name, value in values.items():
        placeholder = "{{" + name + "}}"
        if placeholder not in filled:
            raise KeyError(f"The prompt {prompt.name} holds no placeholder {placeholder}.")
        filled = filled.replace(placeholder, value)
    return filled

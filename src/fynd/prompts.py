"""Load a prompt from disk and hash it.

ADR 0004 keeps every prompt in a file. A reader finds it by the version in the
file name, and the cache key carries the hash of the content.
"""

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

PROMPTS_DIR_VARIABLE: Final = "FYND_PROMPTS_DIR"


@dataclass(frozen=True)
class Prompt:
    """One prompt file, with the hash the cache key needs."""

    name: str
    text: str
    sha256: str


def prompts_dir() -> Path:
    """Returns the directory that holds the prompt files."""
    from_environment = os.environ.get(PROMPTS_DIR_VARIABLE)
    if from_environment:
        # A test points this at its own directory, so no test depends on the
        # wording of a shipped prompt.
        return Path(from_environment)
    # This file is src/fynd/prompts.py, so two levels up is the repository.
    return Path(__file__).resolve().parents[2] / "prompts"


def load(name: str) -> Prompt:
    """Reads the prompt file called `name` and hashes its content."""
    # The hash covers the whole file, so a typo fixed without a rename still
    # misses the cache. No published number then belongs to a lost prompt.
    path = prompts_dir() / f"{name}.md"
    text = path.read_text(encoding="utf-8")
    return Prompt(name=name, text=text, sha256=hashlib.sha256(text.encode("utf-8")).hexdigest())


def fill(prompt: Prompt, values: dict[str, str]) -> str:
    """Replaces every `{{PLACEHOLDER}}` in the prompt with its value."""
    filled = prompt.text
    for name, value in values.items():
        placeholder = "{{" + name + "}}"
        # The braces matter. Without them the name DOMAIN would replace the
        # first half of DOMAIN_NAME and leave the rest behind.
        if placeholder not in filled:
            raise KeyError(f"The prompt {prompt.name} holds no placeholder {placeholder}.")
        filled = filled.replace(placeholder, value)

    # A placeholder left behind would travel to the model as braces, and the
    # prompt hash would not show the mistake.
    if "{{" in filled:
        raise KeyError(f"The prompt {prompt.name} still holds a placeholder after filling.")
    return filled

"""Loads saved AI instructions and fills their placeholders for Stage 2.

Stage 2 reads prompts/propose-topics-v1.md, inserts the Domain and other values,
and passes the filled text to the Claude client. The file hash identifies the
original wording for caching and measurements (ADR 0004).
"""

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final

PROMPTS_DIR_VARIABLE: Final = "FYND_PROMPTS_DIR"


@dataclass(frozen=True)
class Prompt:
    """One prompt's name, original text, and content hash."""

    name: str
    text: str
    sha256: str


def prompts_dir() -> Path:
    """Returns the directory that holds the prompt files."""
    from_environment = os.environ.get(PROMPTS_DIR_VARIABLE)
    if from_environment:
        # Tests use temporary files without changing the shipped prompts.
        return Path(from_environment)
    # Locate the repository from this file, regardless of the working directory.
    return Path(__file__).resolve().parents[2] / "prompts"


def load(name: str) -> Prompt:
    """Reads <name>.md and hashes its original text."""
    path = prompts_dir() / f"{name}.md"
    text = path.read_text(encoding="utf-8")
    # Hash the text so wording changes invalidate the cache without a file rename.
    return Prompt(name=name, text=text, sha256=hashlib.sha256(text.encode("utf-8")).hexdigest())


def fill(prompt: Prompt, values: dict[str, str]) -> str:
    """Replaces every `{{PLACEHOLDER}}` in the prompt with its value."""
    filled = prompt.text
    for name, value in values.items():
        placeholder = "{{" + name + "}}"
        # Match the braces too, so DOMAIN cannot partially replace DOMAIN_NAME.
        if placeholder not in filled:
            raise KeyError(f"The prompt {prompt.name} holds no placeholder {placeholder}.")
        filled = filled.replace(placeholder, value)

    # Reject incomplete instructions before they reach the model.
    if "{{" in filled:
        raise KeyError(f"The prompt {prompt.name} still holds a placeholder after filling.")
    return filled

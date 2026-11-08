"""Sends Stage 2's Topic instructions to Claude and caches its JSON answer.

Stage 2 supplies the filled prompt and expected response fields. This client
handles the API request and JSON parsing; Stage 2 checks whether the returned
Topics are usable. Tests supply a fake model function instead (ADR 0006).
"""

import hashlib
import json
from typing import Any, Final

import anthropic

from fynd import cache

# Stage 2 uses Haiku 4.5 to propose Topics.
HAIKU: Final = "claude-haiku-4-5"

# Limit the reply length; this is not a total Project spending cap.
MAX_TOKENS: Final = 4000


class ModelRefused(Exception):
    """Raised when Claude refuses, truncates, or returns unusable JSON text."""


def ask_for_json(
    filled_prompt: str,
    prompt_sha256: str,
    schema: dict[str, Any],
    schema_version: int,
    model: str = HAIKU,
) -> Any:
    """Returns parsed JSON from the cache or a Claude request."""
    parts = {
        "model": model,
        "prompt_sha256": prompt_sha256,
        "input_sha256": hashlib.sha256(filled_prompt.encode("utf-8")).hexdigest(),
        # No decoding settings are sent; repeatability comes from cached answers.
        "max_tokens": MAX_TOKENS,
        # The caller must bump this version when the response schema changes.
        "schema_version": schema_version,
    }
    key = cache.cache_key("claude", parts)
    cached = cache.read(key)
    if cached is not None:
        return cached

    client = anthropic.Anthropic()
    # Request the Stage's response shape; Stage rules still check its usefulness.
    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": filled_prompt}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )

    # Truncated replies can still contain text, so check the stop reason first.
    if response.stop_reason in ("max_tokens", "refusal"):
        raise ModelRefused(
            f"The model {model} stopped with the reason {response.stop_reason}. "
            f"Raise MAX_TOKENS, now {MAX_TOKENS}, if the answer was simply too long."
        )

    text = ""
    for block in response.content:
        if block.type == "text":
            text = block.text
            break
    if not text:
        raise ModelRefused(
            f"The model {model} returned no text to read. Stop reason: {response.stop_reason}."
        )

    try:
        value = json.loads(text)
    except json.JSONDecodeError as error:
        raise ModelRefused(f"The model {model} returned text that is not JSON: {error}.") from None

    cache.write(key, parts, value)
    return value

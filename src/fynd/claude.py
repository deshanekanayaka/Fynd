"""Ask Claude for one answer in a fixed shape.

This file is an edge. A Stage receives it as a plain function argument, so a
test runs the Stage with no network and no token spend. See ADR 0006.

Two rules from ADR 0004 live here. Temperature is zero, so the same question
returns the same answer. Every reply is cached under a key that holds the
model, the hash of the prompt file, the hash of the filled prompt, the decoding
parameters, and the version of the shape asked for.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import anthropic

from fynd import cache

# The PRD gives the Topic proposal and the Claim extraction to Haiku 4.5.
HAIKU = "claude-haiku-4-5"

# Decoding is fixed. See ADR 0004.
TEMPERATURE = 0
MAX_TOKENS = 4000


class ModelRefused(Exception):
    """Raised when the model returns nothing Fynd can read.

    Three cases reach it. The reply holds no text block, the reply stopped
    because it hit the token ceiling or a safety rule, or the text is not the
    JSON the schema asked for. None of the three is cached, so the next run
    asks again.
    """


def ask_for_json(
    filled_prompt: str,
    prompt_sha256: str,
    schema: dict[str, Any],
    schema_version: int,
    model: str = HAIKU,
) -> Any:
    """Return the answer to one prompt, as data in the shape the schema names.

    The schema travels from the Stage, because the shape of an answer is a rule
    of the Stage and not a detail of this client.
    """
    parts = {
        "model": model,
        "prompt_sha256": prompt_sha256,
        "input_sha256": hashlib.sha256(filled_prompt.encode("utf-8")).hexdigest(),
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "schema_version": schema_version,
    }
    key = cache.cache_key("claude", parts)
    cached = cache.read(key)
    if cached is not None:
        return cached

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        messages=[{"role": "user", "content": filled_prompt}],
        output_config={"format": {"type": "json_schema", "schema": schema}},
    )

    # A reply that stopped early is not an answer. A truncated reply still
    # carries a text block, so the stop reason is the only honest check, and
    # without it the broken JSON would raise far from the cause.
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

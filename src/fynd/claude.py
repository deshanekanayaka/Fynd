"""Ask Claude for one answer in a fixed shape.

An edge, not a rule. A Stage receives this function as an argument, so a test
runs the Stage with no network and no spend. See ADR 0006.
"""

import hashlib
import json
from typing import Any, Final

import anthropic

from fynd import cache

# The PRD gives the Topic proposal and the Claim extraction to Haiku 4.5.
HAIKU: Final = "claude-haiku-4-5"

# ADR 0004 fixes decoding, so the same question returns the same answer.
TEMPERATURE: Final = 0
MAX_TOKENS: Final = 4000


class ModelRefused(Exception):
    """Raised when the model returns nothing Fynd can read.

    No text block, a reply that stopped early, or text that is not JSON. None
    of the three is cached, so the next run asks again.
    """


def ask_for_json(
    filled_prompt: str,
    prompt_sha256: str,
    schema: dict[str, Any],
    schema_version: int,
    model: str = HAIKU,
) -> Any:
    """Returns the model's answer to one prompt, in the shape the schema names.

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

    # A truncated reply still carries a text block, so the stop reason is the
    # only honest check. Without it the broken JSON raises far from the cause.
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

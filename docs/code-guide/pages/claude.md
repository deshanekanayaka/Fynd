---
id: "claude"
title: "claude.py"
group: "External services"
order: 207
source: "src/fynd/claude.py"
summary: "Sends a filled prompt to Claude and returns a structured JSON answer, reusing cached answers when available."
related: ["stage2", "prompts", "cache"]
note: "No temperature or other decoding parameter is sent. A fresh model call may differ; repeatability comes from replaying the saved answer. JSON shape alone does not prove that a Topic meets the product rules."
updated: "2026-11-08"
---

## Why this file exists

Stage 2 decides what Topics should look like. This file handles the service request, response parsing, and caching, so the Stage can be tested with a fake model function.

The actual instructions come from `prompts.py`; the expected JSON fields come from Stage 2. This client sends both to Claude. The SDK reads `ANTHROPIC_API_KEY` from the environment when a live request is needed.

## The flow

1. **Check cache**

   Use model, prompt hash, input hash, token limit, and schema version.

2. **Ask Claude**

   Request the Stage’s JSON schema with claude-haiku-4-5 by default.

3. **Read answer**

   Reject refused, truncated, missing, or non-JSON text before caching it.

## A small example

```text An answer shape — simplified
{
  "topics": [
    {"label": "Household energy forecasting",
     "query": "household electricity demand forecasting"}
  ]
}
```

### What does the schema do?

The schema describes the expected fields and types. For Topic generation, it asks for a `topics` list whose entries contain `label` and `query` strings. It controls response structure, not whether an offered Topic is useful or has enough literature.

### What identifies a cached answer?

The model identifier, original prompt hash, filled-input hash, reply-token limit, and schema version all contribute to the key. For example, changing the Domain changes the filled text and produces another key. Changing the response schema requires the caller to bump its version; the schema itself is not hashed here.

### What happens to a broken answer?

The client rejects explicit refusals, answers stopped by the token limit, missing text, and text that cannot be parsed as JSON. These answers are not cached. It reads the first text block and uses `json.loads` to turn it into a Python value.

The client does not separately validate the parsed value against the schema. Stage 2 still filters unusable Topic entries and can retry a list with too few usable Topics. SDK or connection errors propagate to the CLI's error handler.

### What are the 4,000 tokens for?

`MAX_TOKENS` limits the length of the generated reply. Tokens are pieces of text rather than a fixed number of words. This setting does not cap the whole Project's API spending.

## The pieces inside

| Name                 | What it does                                                                       |
| -------------------- | ---------------------------------------------------------------------------------- |
| `HAIKU / MAX_TOKENS` | The default model identifier and the 4,000-token response limit.                   |
| `ModelRefused`       | Raised when the response cannot be used as JSON or stops early.                    |
| `ask_for_json`       | Reads a cached answer or sends the request, parses its text, and saves the result. |

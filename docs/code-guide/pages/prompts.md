---
id: "prompts"
title: "prompts.py"
group: "Shared foundations"
order: 3
source: "src/fynd/prompts.py"
summary: "Loads a saved prompt, hashes its wording, and fills its placeholders before an AI request."
related: ["stage2", "claude", "cache"]
note: "Only propose-topics-v1.md currently exists. Claim extraction and Proposal drafting prompts are planned work."
updated: "2026-11-08"
---

## Why this file exists

A prompt edit can change the answer. Hashing the whole file makes that edit part of the cache identity, even when the filename stays the same.

A prompt is saved text containing instructions for the AI. Stage 2 currently loads `prompts/propose-topics-v1.md`, which asks Claude to propose Topics. This module only prepares that text; `claude.py` sends the request.

## The flow

1. **Load**

   Read `prompts/<name>.md`, keeping the original text and its hash.

2. **Fill**

   Replace placeholders with values such as the Domain.

3. **Send**

   Stage 2 passes the filled prompt and original file hash to the model client.

## A small example

```text Replacing one placeholder
Prompt text:  Propose Topics inside {{DOMAIN_NAME}}.
Values:       {"DOMAIN_NAME": "energy"}
Filled text:  Propose Topics inside energy.
```

The original `Prompt` stays unchanged. `fill` returns a new string; it does not edit the file or call the AI.

### Why are there two hashes?

The hash stored in `Prompt.sha256` identifies the original file wording. The Claude client separately hashes the filled text, so using Energy instead of Technology also creates a different cache entry.

### What happens if a placeholder is wrong?

If the file contains `{{DOMAIN_NAME}}` but the supplied dictionary uses `DOMAIN`, `fill` raises `KeyError` rather than replacing part of the name. It also raises if a placeholder is left unfilled. Repeated occurrences of the same placeholder are all replaced.

## The pieces inside

| Name          | What it does                                                                         |
| ------------- | ------------------------------------------------------------------------------------ |
| `Prompt`      | The filename stem, original text, and SHA-256 hash.                                  |
| `prompts_dir` | Uses FYND_PROMPTS_DIR when set; otherwise finds the repository’s prompts directory.  |
| `load`        | Reads the named .md file and hashes its complete text.                               |
| `fill`        | Replaces exact {{PLACEHOLDER}} strings and rejects missing or leftover placeholders. |

`Prompt` is a frozen dataclass: its fields cannot be reassigned after creation. `name` is the filename without `.md`, `text` is the unfilled wording, and `sha256` is its 64-character hash. The directory defaults to the repository's `prompts/` folder; `FYND_PROMPTS_DIR` can point tests at temporary files. A missing prompt file raises `FileNotFoundError`.

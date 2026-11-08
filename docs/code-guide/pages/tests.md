---
id: "tests"
title: "tests/"
group: "Running and checking"
order: 622
source: "tests"
summary: "Checks the product promises and known failure cases with fake services and local files."
related: ["cache", "prompts", "stage2", "retrieval", "cli"]
note: "290 tests were collected on 2026-11-08. Count alone does not establish quality or redundancy. Live service behaviour and changed model prompts need separate dated measurements."
updated: "2026-11-08"
---

## Why this file exists

A refactor should preserve behaviour that matters: stable cache keys, refused unoffered Picks, ranking order, and careful handling of incomplete service replies. Fake clients check those paths without paying for requests.

## The flow

1. **Arrange**

   Set up local inputs, a temporary cache, and fake replies.

2. **Run**

   Call the same functions used by the CLI.

3. **Check**

   Assert the promised outcome or failure.

## A small example

```text An existing cache promise
first = cache.cache_key("claude", {"a": 1, "b": 2})
second = cache.cache_key("claude", {"b": 2, "a": 1})
assert first == second

# Field order must not create a different request identity.
```

```sh Run local checks
uv run pytest
uv run ruff check src tests

# A focused check while reviewing cache.py:
uv run pytest tests/test_cache.py -q
```

## The pieces inside

| Name                            | What it does                                                                                |
| ------------------------------- | ------------------------------------------------------------------------------------------- |
| `Cache and prompts tests`       | Check request identity, saved answers, file companions, refusals, and placeholder handling. |
| `Stage tests`                   | Check offered Picks, Topic parsing, retries, and candidate thresholds.                      |
| `Service tests`                 | Use fake HTTP/model replies to check fields, caching, pacing, and failures.                 |
| `Fetching and extraction tests` | Check robots rules, byte limits, PDF layouts, HTML extraction, and text quality.            |
| `Retrieval tests`               | Check ranking behaviour, vector compatibility, fusion reasons, and metric calculations.     |
| `tests/files/`                  | Local fixtures, graded sets, and a helper that creates a two-column PDF.                    |

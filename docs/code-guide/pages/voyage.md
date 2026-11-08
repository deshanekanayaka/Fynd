---
id: "voyage"
title: "voyage.py"
group: "External services"
order: 210
source: "src/fynd/voyage.py"
summary: "Gets text embeddings and reranking scores from hosted Voyage models, with caching and request pacing."
related: ["retrieval", "retrieval-report", "cache", "cli"]
note: "The code uses voyage-3.5-lite, defaults to 1024 dimensions, and measures 512 too. It configures rerank-3-lite; availability still needs checking in #37. Its 21-second pacing and token estimates are local settings, not a guarantee of account limits."
updated: "2026-11-08"
---

## Why this file exists

Keyword matching misses related wording. Embeddings help compare meaning; reranking considers a query alongside each document. Saving individual embeddings avoids paying again for overlapping Paper lists.

## The flow

1. **Texts**

   Receive the query or Paper titles and abstracts.

2. **Missing work**

   Load cached vectors; group uncached texts into estimated token batches.

3. **Vectors or scores**

   Call the hosted model and return the results in usable order.

## A small example

```text An embedding request — simplified
model: voyage-3.5-lite
input_type: query
output_dimension: 1024
input: ["household energy forecasting"]

output: [[0.12, -0.08, ...]]  # 1,024 numbers, illustrative values
```

### Why cache one vector per text?

```text Illustrative overlapping requests
First pool: ["Paper A", "Paper B"] → request A and B
Next pool:  ["Paper B", "Paper C"] → reuse B; request only C
Return the next pool's vectors in B, C order.
```

The cache identity includes the text, embedding model, query/document mode, dimensions, and request-shape version. Changing any of those settings produces a different entry. Duplicate uncached text is sent once; the returned list restores its original positions. Entirely cached or empty inputs make no request, so no live API key is needed by this client for those paths.

### What is a slice?

It is a batch of texts sent in one embedding request. `estimated_tokens` uses `len(text) // 4 + 1`, and `slices` groups texts around a 3,000-estimated-token budget. This is a character-based estimate, not the model's tokenizer. A single oversized text is sent alone rather than split or dropped, so the budget is not a hard upper bound on every request.

The embedding request uses `voyage-3.5-lite`, with 1024 dimensions by default. The measurement also requests 512. The current host is `https://ai.mongodb.com/v1`, and the client requires a `VOYAGE_API_KEY` beginning with `al-` before making a live request. These are the project's configured choices, not automatic account or region discovery.

### How long does it wait?

| Setting          | Value                  | What the code does                                                                 |
| ---------------- | ---------------------- | ---------------------------------------------------------------------------------- |
| Request gap      | 21 seconds             | Waits the remaining time between request starts; the first request is immediate.   |
| Rate-limit retry | 60 seconds             | Retries HTTP 429 once after a wait, then raises `RateLimited` if it happens again. |
| HTTP timeout     | 60 seconds             | Configures the default HTTP client's network timeout.                              |
| Batch budget     | 3,000 estimated tokens | Groups ordinary texts into batches; a single oversized text is an exception.       |

Other HTTP errors and connection or timeout exceptions propagate without this retry. Timing is per client instance. These settings do not discover current provider limits or enforce a Project-wide spending ceiling.

### How is reranking different?

Reranking sends the query and the whole ordered document list together, using `rerank-3-lite`. That complete input identifies one cached response. Results contain zero-based indexes into the original document list and relevance scores.

```text Illustrative reranking reply
Documents: ["far from the subject", "close to the subject"]
Returned pairs: [(1, 0.9), (0, 0.2)]

Index 1 names the second input document; it does not mean rank 1.
The scores are sorting values, not probabilities.
```

An empty result for non-empty documents raises `ReplyIncomplete` without caching that result. Missing embeddings also raise, while successfully returned individual vectors can remain cached for a later run. `tokens_used` accumulates service-reported usage for live responses; cache hits do not increase it. It is not a currency amount or a complete billing ledger.

### Existing response checks still to fix

Fake replies reproduced two gaps: an embedding index of `-1` selects the last input text using Python indexing and is cached without rejection; a non-empty reranking reply missing a score is cached before parsing raises `KeyError`. The second call then repeats that failure from disk. Both are recorded in [bugs.md](../bugs.md) for correction before issue #37's failed-reply caching promise is accepted. This readability pass does not change validation behaviour.

## The pieces inside

| Name                                         | What it does                                                                           |
| -------------------------------------------- | -------------------------------------------------------------------------------------- |
| `KeyMissing / RateLimited / ReplyIncomplete` | Explain missing or incompatible keys, repeated rate limits, and missing results.       |
| `estimated_tokens / slices`                  | Estimate tokens from character count and group texts around a 3,000-token budget.      |
| `Voyage`                                     | Stores the HTTP client, API key, request timing, and tokens reported for live calls.   |
| `embed`                                      | Reuses vectors per text, requests only missing unique texts, and restores input order. |
| `rerank`                                     | Caches the query-and-document request and returns document-index/score pairs.          |
| `embedding_parts / embedding_key`            | Identify a vector by text, model, input type, dimensions, and request shape.           |
| `count_tokens`                               | Adds the service’s reported token usage to the run total.                              |
| `wait_for_the_rate_limit / ask`              | Paces requests, checks the Atlas key prefix, and retries HTTP 429 once.                |

---
id: "retrieval"
title: "retrieval.py"
group: "Ranking Papers"
order: 416
source: "src/fynd/retrieval.py"
summary: "Orders Papers using keyword matches, embedding similarity, combined positions, or a supplied reranker."
related: ["voyage", "retrieval-report", "models"]
note: "These ranking helpers exist, including fusion and reranking, but #37 still needs to wire their measurement rows. The handwritten stemmer is awaiting the agreed library replacement and new measurements."
updated: "2026-11-08"
---

## Why this file exists

A search can return more Papers than later Stages can read. Ranking is meant to put the useful Papers inside the top-20 cut rather than relying on the service’s original order.

## The flow

1. **Text**

   Use each Paper’s title and abstract, or its title alone if no abstract exists.

2. **Rank**

   Calculate keyword or vector similarity scores.

3. **Combine**

   Optionally fuse the lists and rerank them.

## A small example

```text Why descending order?
Paper A → score 8.0
Paper B → score 3.0
Paper C → score 6.0

Descending order: A, C, B
The top cut keeps the strongest matches first.
```

### What does a score mean?

**paper_id** is Semantic Scholar’s identifier for the Paper. A **score** is a method-specific sorting value, not a percentage or a measure of scientific quality. BM25 and cosine scores are on different scales, which is why fusion combines positions.

```text Two ways to match a Topic
Query: household energy forecasting

Paper: Predicting residential electricity demand

BM25 looks for matching word stems.
Dense ranking compares learned representations of the phrases.
```

### Why does fusion have a constant of 60?

It reduces the advantage of the very highest positions. With `K=1`, first place earns about 5.5 times the credit of tenth; with `K=60`, it earns about 1.15 times the credit. This helps Papers that do reasonably well in both rankings. It does not mean “keep 60 Papers.”

`BM25_K1=1.2` controls diminishing returns from repeated query words. `BM25_B=0.75` adjusts for length. `CUT=20` marks the top cut. The ending rules are only `ing`, `es`, `ed`, and `s`; they are not a complete English stemmer.

## The pieces inside

| Name                            | What it does                                                                |
| ------------------------------- | --------------------------------------------------------------------------- |
| `Ranked`                        | One Paper identifier, ranking score, matched stems, and dense top-cut flag. |
| `Embed / Rerank`                | Interfaces for supplied embedding and reranking functions.                  |
| `stem / tokens`                 | Apply the current simple ending rules to lowercased words.                  |
| `document_text / matched_terms` | Build ranking text and collect matched query stems.                         |
| `ordered`                       | Sorts by descending score, then identifier for repeatable ties.             |
| `keep_reasons`                  | Preserves matched terms and the dense flag after reordering.                |
| `bm25_ranking`                  | Rewards matching words, adjusting for rarity, repetition, and text length.  |
| `cosine / dense_ranking`        | Compare query and Paper vectors and order Papers by similarity.             |
| `fuse`                          | Adds 1 / (60 + position) from each input ranking.                           |
| `rerank_ranking`                | Uses a supplied reranker’s scores and checks its document indexes.          |

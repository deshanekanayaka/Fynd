---
id: "retrieval-report"
title: "retrieval_report.py"
group: "Measurements"
order: 519
source: "src/fynd/retrieval_report.py"
summary: "Calculates ranking metrics against human grades and formats the retrieval measurement table."
related: ["retrieval", "retrieval-set", "grading", "measure", "cli"]
note: "The current CLI publishes baseline, query, BM25, and dense rows. Fusion and reranked rows remain issue #37. A good retrieval score does not establish Claim-to-Problem support."
updated: "2026-11-08"
---

## Why this file exists

A ranking needs a measured comparison. This file separates “how many useful Papers did we reach?” from “how well did we order the first results?” and records the pool’s limits.

## The flow

1. **Orders and grades**

   Receive Paper identifier lists plus grades 0–2.

2. **Metrics**

   Calculate recall at 10 and 20, and nDCG at 10.

3. **Markdown**

   Write rows with counts, configuration notes, queries, and limitations.

## A small example

```text Recall versus ordering — illustrative
Pool: 10 relevant Papers
Top 5: 4 relevant Papers

Recall at 5 = 4 / 10 = 40%

nDCG also rewards putting grade-2 Papers before grade-1 Papers.
A perfect nDCG at 10 only describes those first 10 positions.
```

### What does recall count?

Grades 1 and 2 both count as relevant. `recall_at` returns a pair: how many relevant Papers are inside the first `k` positions, and how many relevant Papers exist in the entire graded pool. `rate` then turns that pair into a percentage with counts beside it.

A short query row still uses the full pool denominator. If it contains one relevant Paper out of three relevant Papers in the pool, it gets `33% (1/3)`, not 100%. A top-10 list can recover at most 10 relevant Papers, or fewer if the pool contains fewer than 10.

### What does nDCG add?

Recall treats grades 1 and 2 alike. nDCG also distinguishes their value and position: a grade-2 Paper contributes twice the gain of a grade-1 Paper, and earlier positions count more. `dcg` computes that position-weighted total. `ndcg_at` divides it by the best possible total from the pool's grades.

```text Illustrative nDCG ordering
Pool grades: A=2, B=1, C=0

A, B, C → best order → nDCG is 1.0
C, B, A → useful Papers appear later → lower nDCG
```

Unknown identifiers keep their positions but get zero gain. If there are no relevant Papers, recall is displayed as `- (0/0)` and nDCG returns 0.0 by this implementation's convention.

### What are the row builders comparing?

`rows_from_searches` rebuilds the baseline by alternating the eligible positions from each query, using the same pooling function as the Retrieval set builder. It also produces one row per individual query in its original returned order. Human grades do not determine those orders.

Individual query rows normally contain at most 15 Papers, whereas the baseline and computed rankings draw from the whole pool. A query row cannot fill a top-20 list, so its recall should not be read as an equal-size comparison with the baseline.

`dense_rows` runs each supplied search string at each vector size, normally the Topic label and subject query at 1024 and 512 dimensions. The supplied embedding function handles cache reuse and any live requests. This module does not itself provide an embedding cache.

### What context stays with the numbers?

`Row` keeps the row's name, note, ordered Paper identifiers, and flags indicating a computed Fynd ranking and use of text. These flags control the report's explanatory paragraphs. `report` also records query overlap, missing abstracts, model details from row notes, and the saved set's path.

The reference date fixes the Evidence window; the run date says when the measurement happened. Both are supplied by the caller. The report keeps the stated limitations visible: one human grader, a finite query pool, and a relevance rule that ignores country. It returns Markdown for the CLI to save.

## The pieces inside

| Name                           | What it does                                                                         |
| ------------------------------ | ------------------------------------------------------------------------------------ |
| `Row`                          | A ranking’s name, ordered identifiers, note, and flags about how it was produced.    |
| `rows_from_searches`           | Builds the interleaved arrival-order baseline and individual query rows.             |
| `dense_rows`                   | Builds dense ranking rows at each requested vector size and search string.           |
| `shared_papers / relevant_ids` | Count query overlap and select grade-1 or grade-2 Papers.                            |
| `gain_of / dcg`                | Use the grade as gain and discount later positions.                                  |
| `recall_at`                    | Counts relevant Papers in the top k against every relevant Paper in the graded pool. |
| `ndcg_at`                      | Compares the observed order with the best order allowed by the pool’s grades.        |
| `rate`                         | Formats a percentage with its raw numerator and denominator.                         |
| `report`                       | Builds the Markdown table and its reproducibility notes.                             |

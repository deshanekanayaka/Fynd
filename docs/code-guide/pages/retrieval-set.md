---
id: "retrieval-set"
title: "retrieval_set.py"
group: "Measurements"
order: 517
source: "src/fynd/retrieval_set.py"
summary: "Builds a shuffled pool of Papers that a person can grade to evaluate retrieval."
related: ["semantic-scholar", "grading", "retrieval-report", "cli"]
note: "The committed set excludes abstracts. Ranking measurements need the corresponding local search cache; recall only covers Papers in this pool, not all research."
updated: "2026-11-08"
---

## Why this file exists

We cannot say a ranking is useful just because its results look plausible. A fixed Retrieval set gives several rankings the same Papers and human Relevance grades to compare against.

## The flow

1. **Four queries**

   Search the same Seeded Topic with four handwritten phrasings.

2. **Pool**

   Take up to 15 from each, deduplicate identifiers, and cap at 60.

3. **Shuffle**

   Use a fixed seed before a person grades the 40–60 Papers.

## A small example

```text What is saved in the set — simplified
{
  "topic": "United Kingdom household energy forecasting",
  "topic_query": "household energy forecasting",
  "reference_date": "2026-10-20",
  "entries": [
    {"paper_id": "example-id", "title": "Example Paper",
     "grade": null, "queries": ["wider"]}
  ]
}
```

### Why request 50 Papers but keep only 15 per query?

The search request size is 50, matching the intended retrieval-search design. The evaluation pool takes only the first 15 from each of four queries, giving at most 60 Papers before removing overlap. This keeps human grading manageable. The current Stage 2 CLI still searches 20; connecting the planned 50-to-20 ranking is separate work under issue #39.

The pool must contain at least 40 distinct Papers. If results are sparse or several queries find the same Papers, `build_set` raises `SetTooSmall` rather than quietly building an undersized set.

### How are overlaps handled?

```text Illustrative alternating-query pool
Query A: Paper 1, Paper 2
Query B: Paper 2, Paper 3

Take A's first, B's first, A's second, B's second.
Distinct pool: Paper 1, Paper 2, Paper 3
Paper 2 records both query names.
```

`entries_from` merges by Paper identifier. The queries take turns so a cap does not let the first query dominate the pool. Even after the pool is full, the scan continues to record additional query names for Papers already retained. `papers_offered` counts unique eligible Papers before the overall cap, not every Paper in the full 50-result replies.

### Why shuffle with a fixed seed?

Reading Papers in the search's rank order can influence human grading. Shuffling reduces that cue, and the fixed seed `20261020` makes the same input list produce the same order again. The number is a chosen seed, not a date filter. The function copies the list before shuffling it; it does not reorder the caller's list.

### What does the reference date do?

`reference_date` fixes the Evidence window used to build the set. For example, a 2026 reference date produces a first accepted year of 2022. Replaying that set later should keep using its saved reference date rather than the current calendar year.

`topic` holds the display label, including the place. `topic_query` holds the subject words for ranking, without the place. The four pool-building queries are handwritten phrasings of the same Seeded Topic; this measurement does not assess the quality of AI-generated search queries.

### What is kept out of the saved entries?

Each `SetEntry` contains the Paper identifier, title, query names, and an optional Relevance grade. `None` means ungraded; only 0, 1, and 2 are accepted as grades. Abstracts stay out of the committed set under ADR 0011, and years are omitted from entries because grading ignores them.

The CLI later supplies search replies containing the abstracts. `pool_papers` selects only retained identifiers from those replies; it does not fetch anything or read cache files itself. `papers_without_abstract` counts missing text so the report can disclose it.

## The pieces inside

| Name                                       | What it does                                                                    |
| ------------------------------------------ | ------------------------------------------------------------------------------- |
| `SeedQuery / SetEntry / RetrievalSet`      | Describe a search phrasing, a Paper awaiting a grade, and the saved set.        |
| `SetTooSmall / Search`                     | The insufficient-pool error and supplied search interface.                      |
| `SEED_QUERIES`                             | Four handwritten search phrasings, not AI-generated Topics.                     |
| `entries_from`                             | Pools results one position per query at a time and records overlapping queries. |
| `pool_papers`                              | Rebuilds the graded pool with locally cached abstracts for ranking.             |
| `papers_without_abstract / papers_offered` | Count missing abstracts and unique Papers offered before the cap.               |
| `shuffled`                                 | Changes the entry order reproducibly without altering the input list.           |
| `build_set`                                | Runs the searches using a passed reference date and returns the ungraded set.   |

# How well a ranking orders the Retrieval set

Measured on 2026-10-22 by `uv run python -m fynd.cli measure-retrieval --as-of 2026-10-20`.

The pool is the 60 Papers of [retrieval-set-2026-10-20.json](../../tests/files/retrieval-set-2026-10-20.json), each with a Relevance grade written by hand. 39 of them count as relevant, which is every Paper graded 1 or 2. The set was built on 2026-10-20, and that date fixes the Evidence window of every search behind it.

Recall at 20 is the headline, because 20 is the cut a Project is built on. See [ADR 0013](../adr/0013-retrieval-ranks-in-python-over-a-pool-cut-to-20.md).

The gain of a Paper in nDCG is its grade, so a 2 is worth twice a 1. That is the original linear form, and it is a stated default and not a choice made against these numbers.

The two kinds of number answer two questions. Recall at 10 cannot pass 10 of 39 Papers, which is 26%, because there are only 10 places. So nDCG at 10 says how well a row ordered the Papers it put in those places, and recall says how much of the pool it reached.

8 Papers of the pool carry no abstract, so a row that reads text reads the title of those alone. That cuts both ways. A title is a short document, and BM25 divides a score by the length, so a title that holds a query word scores higher than a long abstract that holds it once. The abstracts are read from the search cache on the machine that runs this command, and they enter no file. See [ADR 0011](../adr/0011-the-public-repository-holds-the-text-and-not-the-files.md).

A query row is not comparable with the baseline. One query returned 15 Papers of the pool, so a query row cannot fill 20 places however good its order is, while the baseline chooses its places from the whole pool. The query rows compare with each other, and the spread between them is the finding.

## The rows

| Row | Recall at 20 | Recall at 10 | nDCG at 10 | What it ranks |
|---|---|---|---|---|
| Baseline | 44% (17/39) | 23% (9/39) | 0.897 | The four searches as they arrived, one rank at a time |
| hand | 21% (8/39) | 18% (7/39) | 0.569 | The `hand` query alone, as it arrived |
| wider | 36% (14/39) | 23% (9/39) | 0.922 | The `wider` query alone, as it arrived |
| narrower | 33% (13/39) | 23% (9/39) | 0.887 | The `narrower` query alone, as it arrived |
| reworded | 10% (4/39) | 8% (3/39) | 0.409 | The `reworded` query alone, as it arrived |
| BM25 | 31% (12/39) | 18% (7/39) | 0.561 | BM25 over the pool, for the Topic `United Kingdom household energy forecasting` |

## The queries

The pool was built by 4 queries, 15 Papers from each. They share no Paper at all, so a query row reaches only the Papers of its own query.

| Query | Text |
|---|---|
| hand | `United Kingdom household energy forecasting` |
| wider | `household energy demand forecasting` |
| narrower | `United Kingdom smart meter load forecasting` |
| reworded | `domestic electricity consumption prediction United Kingdom` |

## The limits

One person wrote every published grade, because Fynd is the project of one student. There is no agreement number between two people, and no published number here is scored against a model pass.

Recall over a pool is recall inside the pool. A relevant Paper that none of the four queries returned is invisible to every number above, and a Paper in a row that nobody graded counts as nothing.

No number says whether Fynd finds United Kingdom evidence, because the grading rule ignores the country by design.

Every constant sits at its published default and no constant was tuned. Tuning against the same 60 Papers this table reports would fit the set.

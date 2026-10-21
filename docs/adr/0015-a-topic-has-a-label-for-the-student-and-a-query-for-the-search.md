---
status: accepted
date: 2026-10-22
---

# A Topic has a label for the student and a query for the search

A Topic carries two strings. The label is what a student reads, and it names the place, as "United Kingdom household energy forecasting" does. The query is what the search and every ranking read, and it names the subject alone, as "household energy forecasting" does.

The place never enters the query. It belongs to the Problem and to the Statistic that proves the Problem is real.

## Why

A Problem belongs to a place. A final year project is set in the United Kingdom, a supervisor reads that, and `CONTEXT.md` gives the place to a Statistic.

A Paper is not the Problem. A Paper is evidence for the Existing approach and the Technical core, and a method a student copies does not change at a border. A model that forecasts household demand in Spain tells a student the same thing it tells a reader in Britain. The grading rule says so already. It asks whose energy a Paper is about and whether the Paper predicts, and it ignores the country. The day 10 entry of `NEXT-STEPS.md` reasoned that out and corrected it.

Asking a search for the place also shrinks the pool for no gain. Few Papers name a country in the title or the abstract. So a country word rewards the Papers that mention it, and not the Papers that do the work.

## The measurement behind it

The table of 2026-10-20 publishes both. BM25 asked for the label reaches 12 of the 39 relevant Papers inside the top 20. BM25 asked for the query reaches 20, and its nDCG at 10 goes from 0.561 to 0.945.

The reason is the arithmetic of BM25. A word counts for more the fewer documents hold it, and "kingdom" sits in 23 of the 60 Papers while "forecast" sits in 44. So the place word outweighed the subject word. An ultra-processed food Paper graded 0 reached place 10, because its abstract names United Kingdom households and energy.

The order of events is stated plainly, because it matters. A diagnosis found the gap after the first BM25 row went into the table. The decision came after it, for the reason above, which rests on `CONTEXT.md` and not on the score. Both rows stay in the table, so no reader has to take that on trust.

## Consequences

`stage2.py` holds `SEEDED_TOPIC` and `SEEDED_TOPIC_QUERY`. A `Topic` already carried `label` and `query` as separate fields, fixed by [ADR 0002](./0002-topics-are-generated-then-verified.md), and nothing had used the difference.

A Retrieval set records `topic_query` beside `topic`. A later run then ranks with the string that built the set, and never with a constant that moved since. A set with no `topic_query` stops the measurement with a sentence instead of ranking with the label.

The prompt that asks a model for Topics has to carry this rule. The `query` it writes then names the subject, and the `label` names the place. Issue 38 checks the query the model writes, and that check gains this rule.

The published table holds a row for each string. A table that showed only the better one is a configuration chosen after the numbers. The file promises that nothing was tuned against these 60 Papers.

## Considered options

Keep the place in one query and accept the number. Rejected. The ranking then chases a word the grading rule throws away, and a student gets Papers that name Britain in place of Papers that do the work.

Filter the Papers to the United Kingdom instead of ranking on the place. Rejected. Semantic Scholar gives a Paper no country field, so the only filter available is the word again. The grading rule also calls a Spanish household forecasting Paper a 2, so such a filter throws away Papers the grades call relevant.

Change the Seeded Topic to drop the place. Rejected, because the Problem really is set in the United Kingdom and a supervisor reads the label. The place leaves the query and stays on screen.

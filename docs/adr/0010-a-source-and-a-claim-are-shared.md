---
status: accepted
date: 2026-10-08
---

# A Source and a Claim are shared, and a Claim carries its prompt hash

One real Source is one `source` row, whatever Project found it. A `claim` row belongs to its Source and not to a Project. A `claim` row also records the hash of the prompt that produced it, and Fynd reuses only the Claims that the current prompt produced.

## Why sharing is right

The weak reason is cost. The same Paper is fetched once and extracted once. Semantic Scholar allows one request per second, so a second Project on the same Topic pays nothing.

The strong reason is correctness. The Gap bar demands 3 Claims from independent Sources. If one real paper exists as two rows, the independence check counts it twice, and one paper passes the bar twice over. The identifier deduplication and the coauthor rule of day 10 read the same rows. Duplicate rows corrupt that published number too.

One row for one real Source is what makes the word independent mean anything.

## Why the prompt hash goes on the Claim

A shared `claim` row outlives the prompt that wrote it. Without the hash, a new Project silently reuses Claims from an older prompt, and a published number then mixes two prompts.

[ADR 0004](./0004-replayable-runs-and-versioned-prompts.md) already demands the model identifier and the prompt hash on every evaluation result. A stored Claim now obeys the same rule.

Nothing in the cache is deleted when a prompt changes, and nothing in the `claim` table is deleted either. The old rows stay as the evidence behind the old number.

## Consequences

The `claim` table gains `prompt_sha256`. A unique index over the Source, the text kind, the two offsets, and that hash stops the same extraction from landing twice.

Extraction after a prompt change costs money again for a Paper that Fynd already read. That cost is the price of a number that belongs to one prompt.

A Project reads Claims through its own `candidate_problem_claim` links, so sharing changes nothing a student sees.

## Considered options

A `claim` row for each Project. Rejected because the independence rule then counts one paper twice, and the extraction bill repeats for every Project.

A shared Claim with no prompt hash. Rejected because the published numbers then mix prompts, and nothing says which prompt wrote which row.

Deleting old Claims on a prompt change. Rejected for the reason ADR 0004 gives for the cache. The old answer is the evidence behind the old number.

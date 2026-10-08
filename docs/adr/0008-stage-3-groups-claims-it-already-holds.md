---
status: accepted
date: 2026-10-08
---

# Stage 3 gathers the evidence first, and groups Claims it already holds

Stage 3 does not draft a Problem and then look for evidence. It gathers Claims for the kept Topic, verifies each one, and then groups the verified Claims into 3 candidate Problems. The drafting call groups evidence. It does not invent a Problem.

## The decisions

### The order

`offer` runs in this order. Search for the Papers of the kept Topic. Search once on the web for a Statistic and a Product. Fetch and extract every page. Extract Claims with Haiku 4.5. Pass each Claim through the verifier. Group the survivors into 3 candidate Problems with one drafting call.

### The Source text at stage 3

Stage 3 runs before stage 4, so Fynd holds no Open copy of a Paper. The abstract is the Source text for a Paper at stage 3.

A `source` row therefore holds two texts, each with its own hash. The abstract, and the Source text of the Open copy that stage 4 fetches later. A `claim` row carries one more column that names which of the two texts its offsets belong to.

Without that column a stage 5 extraction makes every stage 3 Claim read as stale, because the hash of the new text differs. A second `source` row for the same Paper was rejected, because it breaks the unique index on the identifier.

### The Statistic and the Product

The web search tool on the Anthropic API returns the links. Fynd holds that key already, so no new vendor enters the stack.

Fynd then fetches each page itself and extracts it with trafilatura. A Claim needs a located span, so a search summary is not evidence. The search reply and every page fetch are cached.

### The pool and the time budget

The pool is all 20 abstracts of the kept Topic, plus at most 6 web pages from 3 search queries. That is about 26 small extraction calls.

The calls run one at a time, and the first run is measured. If the Stage breaks 3 minutes, a concurrency of 4 is the fix, and that number goes in the table.

### What is stored

Every verified Claim becomes a `claim` row. The link table joins only the Claims that a candidate Problem uses. Stage 5 reads the rest, and the dropped Claims feed the rejection histogram of [ADR 0005](./0005-a-claim-is-a-located-span.md).

### A retracted Paper

OpenAlex returns a retraction flag on the lookup that [ADR 0007](./0007-the-open-copy-is-resolved-then-measured.md) already makes for every digital object identifier. A Paper that OpenAlex marks as retracted is dropped, and the drop is counted in the same file as the Claim rejections. The check costs no extra request.

### The Evidence window

A Claim that proves the Problem is real must come from a Source dated within 5 years. The rule holds for a Paper and for a Statistic.

An Existing approach and the Technical core carry no window. A 2018 method paper with a reference implementation is good evidence and a good Technical core. A window throws it away.

The year shows on every Claim.

The window is one named constant, the current year minus 4. Stage 2 and stage 3 search with that year range, so the recent pool is as large as the API makes it. Stage 5 runs a second search with no range for the Existing approaches. The year range is an input to the cache key.

### Too little evidence

Fynd shows the cards that the evidence supports, with one plain sentence that says why there are fewer than 3. It never invents a third card. The student also gets the Topic list again.

If the pool supports no candidate Problem, the Stage returns the student to stage 2. That is the same shape as the stage 4 guard.

### The Re-roll

The round 2 prompt names the 3 rejected statements and asks for different groupings of the same pool. The pool is the expensive part, and it is already cached, so a Re-roll costs one drafting call. This repeats the excluded Topic pattern of [ADR 0002](./0002-topics-are-generated-then-verified.md).

## What this buys, and what it does not

This section exists because the honest version is the one to say out loud.

Fynd cannot produce a ghost reference. A `claim` row is two offsets into a text that Fynd downloaded, plus the hash of that text. There is no column for a sentence a model wrote. A chat assistant with a research mode does cite real links. Its remaining failure is the one this design removes. The link is real, and the sentence credited to it is not in the page.

The answer replays. The prompt is a versioned file, every fetch is cached, and the cache key holds every value that changes the answer. A reviewer runs one command and gets the same handover.

The claim carries a number. Recall and invention rate on a frozen labelled set, published in continuous integration.

Three things stay true, and Fynd states them as limits.

A located quote is not a true quote. The verifier proves that a sentence exists in a Source. The retraction drop is the one real guard on whether that Source holds up, and it is narrow.

The grouping is a model judgment. The guard checks the 2 Claims of a candidate Problem. Nothing checks that the Problem those Claims support is the Problem Fynd stated. Metric 2, the human rubric, is the only check there, and it is a human check.

Currency improves, and it is not solved. The Evidence window keeps an old figure out of the Problem. It does nothing about a field that moved after the newest paper in the pool.

## Consequences

The drafting prompt changes job. It receives a list of verified Claims and returns 3 groupings with a statement, a place, and a group of people for each. It receives no freedom to add a fact.

The numbers from the cached run make the OpenAlex lookup load bearing. Of the 20 Papers, 12 are from 2021 or later. 8 of those 12 carry an Open copy link, and 6 of the 8 are doi.org redirects. The two university repository copies are both older than 2021. So the Evidence window leaves 2 directly fetchable files, and the second resolution is what returns the pool to a usable size.

The stage 2 count follows the window. The threshold of 3 Papers with an Open copy counts Papers inside the window. That count exists to tell the student whether current literature exists.

A cache key changes on 1 January, because the year range is an input. That is correct. A published number belongs to the window it was measured in.

A candidate Problem now depends on the web search step. One of the 2 Claims of a candidate Problem must come from a Statistic or a Product. If that step returns nothing usable, no candidate Problem meets the rule, and the Stage returns the student to stage 2.

## Considered options

Problems first, then evidence for each Problem. Rejected because the citation guard has no exception at stage 3. Fynd drafts three Problems, and then drops the ones whose evidence does not exist. That leaves one card or none.

A global 5 year window on every Source. Rejected because it starves stage 5. An older method paper is the Technical core a bachelor's student can build.

No window at all. Rejected because a 2011 figure reads as current in a handover, and that is the most embarrassing kind of wrong.

Fetching Open copies at stage 3. Rejected because the Stage must return in under 3 minutes, and the Open copy work belongs to stage 4 and stage 5.

A search vendor such as Brave or Tavily for the Statistic step. Deferred, not rejected. It becomes the answer when the Anthropic web search tool returns poor links for an official body. The fetch and extraction code does not change.

Storing only the 6 Claims that reach the cards. Rejected because stage 5 reads the rest, and the dropped ones are the rejection histogram.

A second `source` row for the Open copy of a Paper that already has an abstract row. Rejected because it breaks the unique index on the identifier, and two rows for one Paper then need matching logic.

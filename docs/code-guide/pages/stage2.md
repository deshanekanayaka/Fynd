---
id: "stage2"
title: "stage2.py"
group: "Student journey"
order: 106
source: "src/fynd/stages/stage2.py"
summary: "Asks an AI model for Topics, then checks whether a picked Topic has enough recent Papers with candidate files."
related: ["prompts", "claude", "semantic-scholar", "openalex", "models", "cli"]
note: "Current wiring searches 20 Papers and has no ranking cut. Searching 50 and ranking down to 20 is planned under issue #39. The prompt does not yet enforce ADR 0015’s place/subject distinction; query-rule work is recorded under #38."
updated: "2026-11-08"
---

## Why this file exists

A Topic that sounds interesting may have too little accessible literature. The AI proposes the list; a real search and OpenAlex lookup check the student’s Pick.

## The flow

1. **Propose**

   Ask for 10 Topics; keep 5–8 usable entries.

2. **Pick**

   The student sends an offered Topic’s slug.

3. **Check**

   Search recent Papers and require at least 3 with OpenAlex file candidates.

## A small example

```text From Domain to Topic — illustrative
Domain: energy

AI returns:
  label: Household energy forecasting
  query: household electricity demand forecasting

Python adds:
  slug: household-energy-forecasting

The student picks that slug; only then does the literature check run.
```

A **retry** repairs an unusable model answer. A **Re-roll** asks for a new list after the student rejects the previous one; the previous labels go into the avoidance field. Product rules allow one Re-roll, but the current CLI has no persisted counter to enforce it.

### What gets checked before a Topic is offered?

The model is asked for 10 entries. `topics_from_answer` skips entries without usable label/query fields, creates an ASCII slug from the label, and removes duplicate slugs. At least five surviving entries are required, and at most eight are returned.

If too few survive, a retry note changes the second filled prompt and its cache key. Two undersized lists raise `TopicListUnusable`. That retry applies to list processing; model-client exceptions propagate instead of entering this list-retry path. Prompt rules such as query word count and the label's place wording still need their planned enforcement work.

### What happens after the student picks?

`accept_topic` requires the Pick's slug to match an offered Topic. An unoffered slug is refused before any search. For a valid Pick, it searches with the Topic's subject query and the five-calendar-year Evidence window: in 2026, the first accepted year is 2022.

Each Paper with a DOI is looked up through the supplied resolver. A non-empty OpenAlex candidate list adds one to the Paper count, even if that Paper offers several locations. Papers without a DOI or whose lookup raises `WorkNotRead` add nothing. Transport and timeout exceptions are not caught by this helper.

At least three qualifying Papers returns `TopicKept`; fewer returns `TopicBelowThreshold` with the count, so the caller can keep the offered list available. A below-threshold Topic is a normal decision, not a broken Stage. No file is downloaded and no Claim is extracted here.

### Why is this separate from the CLI?

The Stage owns the Topic acceptance rule. The CLI supplies real service functions, and tests supply fakes. The future runner must use saved offered Topics and enforce saved Re-roll limits; the current command-line path reconstructs offers from the prompt cache and holds no Project state.

## The pieces inside

| Name                                                | What it does                                                                                 |
| --------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| `AskModel / Search`                                 | Interfaces for the model and search functions supplied by the caller.                        |
| `TopicKept / TopicBelowThreshold / TopicNotOffered` | Separate outcomes for an accepted Topic, insufficient file candidates, or an unoffered Pick. |
| `TopicListUnusable`                                 | Raised when two model answers both produce fewer than five usable Topics.                    |
| `first_year_in_window`                              | Starts the five-calendar-year Evidence window: in 2026, this returns 2022.                   |
| `slugify`                                           | Turns a label into lowercase ASCII letters, digits, and hyphens.                             |
| `topics_from_answer`                                | Drops empty entries and duplicate slugs, then builds Topic values.                           |
| `offer_topics`                                      | Fills the prompt, calls the supplied model, and allows one retry for an unusable list.       |
| `count_papers_with_a_candidate`                     | Counts Papers whose DOI resolves to at least one OpenAlex candidate. It downloads no files.  |
| `accept_topic`                                      | Checks the slug, runs the search, and compares the candidate count with the threshold of 3.  |

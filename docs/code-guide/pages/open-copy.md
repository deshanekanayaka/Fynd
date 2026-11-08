---
id: "open-copy"
title: "open_copy.py"
group: "From Paper to text"
order: 314
source: "src/fynd/open_copy.py"
summary: "Connects DOI lookup, downloading, extraction, and text checks for one Paper."
related: ["openalex", "fetcher", "extract", "source-text", "measure"]
note: "The Semantic Scholar fallback is still a candidate: it has not yet been downloaded. This pipeline is runnable from the CLI; the future Stage 4 is not implemented."
updated: "2026-11-08"
---

## Why this file exists

A Paper can have several copies. If one host refuses or one file produces text that fails the checks, another candidate may work. This file manages those attempts and returns a result the measurement code can count.

## The flow

1. **Resolve**

   Get OpenAlex candidates, or a permitted Semantic Scholar fallback.

2. **Try files**

   Fetch, extract, and check each candidate until one gives Usable text.

3. **Explain outcome**

   Return the chosen location, extracted text, tried hosts, and reason.

## A small example

```text Two candidates — illustrative
Candidate 1 → host refuses
Candidate 2 → PDF arrives → extraction passes → Usable text

result.attempts == 2
result.is_usable == True
```

### When is the fallback used?

If the Paper has a DOI, the supplied resolver looks it up first. OpenAlex's candidate list is already ordered and capped at three. If that lookup returns no candidates, the reported Semantic Scholar link can be used if it is non-empty and outside the non-file-host blocklist. With no DOI, only that fallback is considered.

The fallback is not added as a fourth attempt after OpenAlex's candidates all fail. It is also not a recovery path for a raised lookup error; resolver exceptions propagate. No file is downloaded just by building the candidate list.

### What is kept when every candidate fails?

The final result follows this priority:

| Outcome                                              | What the caller receives                                                     |
| ---------------------------------------------------- | ---------------------------------------------------------------------------- |
| A file produces Usable text                          | Return immediately; later candidates are not tried.                          |
| Files arrive, but their text fails checks            | Keep the last failed-text result, even if a later host refuses or times out. |
| No extracted text, but at least one recorded refusal | Keep the last refusal reason.                                                |
| Only temporary download failures                     | Raise the last `FetchFailed` rather than inventing an outcome reason.        |
| No candidate exists                                  | Return an empty result with the lookup or missing-DOI reason.                |

For example, if the first PDF produces short text and the second host refuses, the result keeps `text_too_short`: the pipeline reached extraction, so the retained outcome should explain the text failure.

### What counts as an attempt?

`attempts` is the number of candidate links passed to the download function, not the number of network requests. A cache hit or robots refusal still counts as one attempt, and a downloader's internal retry does not add another candidate attempt. `tried_hosts` preserves the complete attempt order, including attempts after a retained failed-text result.

This file does not cache a combined result or save Stage state. The supplied lookup, download, and extraction functions manage their own caches. Only `FetchFailed` is caught while trying candidates; extraction and text-check exceptions propagate.

### Existing attribution issue

If an earlier host refuses and a later host times out, the current result retains the earlier refusal reason but points to the later host. This can misattribute the refusal in the host report. The case was reproduced with supplied fake functions and logged in [bugs.md](../bugs.md); it is not fixed by this readability pass.

## The pieces inside

| Name                      | What it does                                                                         |
| ------------------------- | ------------------------------------------------------------------------------------ |
| `Fetch / Extract / Check` | Interfaces for the supplied download, extraction, and quality-check functions.       |
| `OpenCopyResult`          | Holds the Paper, outcome reason, chosen location, extracted text, and tried hosts.   |
| `is_usable / attempts`    | Report whether checks passed and how many candidate links were tried.                |
| `fallback_open_copy`      | Wraps a reported Semantic Scholar link if it is non-empty and outside the blocklist. |
| `candidates_for`          | Uses OpenAlex candidates first; fallback is used only when none are offered.         |
| `read_open_copy`          | Tries candidates and returns Usable text or the most informative retained outcome.   |

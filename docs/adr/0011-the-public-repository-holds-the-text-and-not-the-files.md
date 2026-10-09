---
status: accepted
date: 2026-10-09
---

# The public repository holds the extracted text, and not the files it came from

The disk cache keeps every external answer, and git keeps part of it. Git holds the extracted Source text, the OpenAlex answers, and the refusals. Git does not hold the fetched bytes, and it does not hold the Semantic Scholar search replies.

## The conflict this resolves

[ADR 0004](./0004-replayable-runs-and-versioned-prompts.md) says a whole Project replays from disk with no network, so the regression tests repeat and continuous integration needs no key. Metric 1 runs in continuous integration against a labelled set of 10 Sources. A replay needs the cache in git.

The repository is public. The cache holds two kinds of value that Fynd has no right to republish.

The fetched bytes are 12 publisher and repository files for the Seeded Topic. Putting them in a public repository is redistribution, whatever the fetch was allowed to do.

The Semantic Scholar search reply holds 16 full abstracts. `PRD.md` already promises that Fynd shows a short quote with a citation and never republishes a stored abstract in full. A committed reply breaks that promise in the plainest way, which is a file anyone reads.

## The decision

Git holds the OpenAlex answers, which are facts about a record and carry no prose. Git holds the extraction answers, which are the Source text of an Open copy. Git holds the refusals, which are a status and a content type.

Git ignores the fetched bytes and the Semantic Scholar replies. One `.gitignore` rule does it. Everything under `.cache/` stays ignored, and two patterns are un-ignored.

One consequence follows for day 5. The labelled set of 10 Sources is built from Sources whose OpenAlex license is an open one. That text is the text continuous integration replays. The labelled set is hand picked anyway, so this costs a choice and not a number.

## Consequences

A reader clones the repository and runs the test suite with no key and no network, because the text every test reads is in git.

A reader who wants the files runs one command and fetches them again. The measurement file states that, so the gap is visible and not hidden.

Fynd cannot measure a second extraction library in continuous integration, because that needs the bytes. It measures one locally and commits the new text. The extractor name and version sit beside the text, so a reader sees which library produced the committed string.

An open license is now a condition on the labelled set, and not only on what Fynd shows a student.

## Considered options

Commit everything, including the bytes and the abstracts. Rejected because it republishes a publisher's file and a publisher's abstract from a public repository, and the PRD already refuses the second one.

Commit nothing from the cache. Rejected because metric 1 then needs a key and a network in continuous integration, which is the thing ADR 0004 exists to prevent.

Commit the bytes only for a file whose OpenAlex license is a Creative Commons one. Rejected because it asks for a redistribution judgement on each of 12 files. A wrong judgement on one file is a licensing problem in a public repository. The text alone carries no such risk, because Fynd stores it as evidence and shows only a located quote.

Commit a copy of the search reply with every abstract cut to a short quote. Rejected because a cut abstract is neither a legal republication nor a usable replay, so it fails both tests at once.

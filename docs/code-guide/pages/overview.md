---
id: "overview"
title: "Understand the code, one file at a time."
navTitle: "Overview"
group: "Start here"
order: 0
summary: "A plain-language companion to the repository. Find what a file does, why it exists, and how its pieces fit together."
related: []
updated: "2026-11-08"
---

## Start with a familiar question

> **Why save an answer we already have?**
>
> So the same run does not download the same PDFs and pay for the same model calls again. Follow one cache entry from request to disk.
>
> [Walk through the cache →](#cache)

## The code in three connected flows

The project begins with a Domain and narrows to a Topic. Separate commands already fetch and read Papers and measure retrieval. These pieces are not yet a complete seven-Stage application.

### 01 · Offer a Topic

[Stage 1](#stage1) → [Prompt](#prompts) → [Claude](#claude) → [Stage 2](#stage2)

The AI proposes Topics; Python checks the Pick using real literature.

### 02 · Read a Paper

[OpenAlex](#openalex) → [Fetcher](#fetcher) → [Extraction](#extract) → [Text checks](#source-text)

A file candidate becomes Source text only after downloading and extraction.

### 03 · Measure a ranking

[Retrieval set](#retrieval-set) → [Grades](#grading) → [Ranking](#retrieval) → [Report](#retrieval-report)

The same graded pool compares keyword and meaning-based rankings.

## What exists today?

| Available code                                         | Still planned                                                 |
| ------------------------------------------------------ | ------------------------------------------------------------- |
| Stage 1 and Stage 2 command-line paths                 | Stages 3–7 and the student-facing frontend                    |
| Cached API clients, file fetching, and text extraction | Project persistence, the runner, and the complete Claim guard |
| BM25 and dense measurement rows                        | Fusion and reranked measurement rows (#37)                    |
| Fusion and reranking helper functions                  | Connect top-20 ranking to Stage 2 (#39)                       |

## How to use this guide

Choose a file in the left navigation, or search by filename or function. Each walkthrough explains its purpose, shows a small example, and links to the next file in the flow. Examples labelled illustrative are made up to explain the code.

Every Python source file under `src/fynd/` has a walkthrough, including the package markers. The guide also introduces the test suite. It describes the current checkout; the product documents remain the source of truth for intended behaviour.

- [CONTEXT.md · vocabulary](../CONTEXT.md)
- [PRD.md · product](../PRD.md)
- [NEXT-STEPS.md · current work](../../history/next-steps-2026-10.md)
- [ADR 0004 · replay](adr/0004-replayable-runs-and-versioned-prompts.md)

## Maintaining the guide

Each walkthrough is a Markdown file in `docs/code-guide/pages/`. Change its wording and rebuild; the sidebar and page contents are generated. Styling and interactions live in separate files. See the [maintenance instructions](code-guide/README.md) for adding a page and running checks.

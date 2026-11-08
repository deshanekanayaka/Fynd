---
id: "cli"
title: "cli.py"
group: "Running and checking"
order: 621
source: "src/fynd/cli.py"
summary: "Provides terminal commands that connect real clients, Stage rules, extraction, and measurement reports."
related:
  [
    "stage1",
    "stage2",
    "cache",
    "retrieval-set",
    "retrieval-report",
    "measure",
    "tests",
  ]
note: "The CLI does not persist Projects or Stage state. Some commands can call external services and incur cost when the cache is missing. --help and stage1 are safe starting points."
updated: "2026-11-08"
---

## Why this file exists

A runnable command gives each backend component a concrete way to be exercised before the web application exists. This file reads arguments and environment settings; individual modules own the work.

## The flow

1. **Command**

   Read a subcommand and flags.

2. **Wire**

   Construct clients and pass their functions into the Stage or measurement.

3. **Output**

   Print decisions or write dated measurement files.

## A small example

```text Safe first command
uv run python -m fynd.cli stage1 --domain energy

# Offers technology and energy, then prints the Domain decision.
# This command makes no external request.
```

```sh Commands that may fetch or spend
uv run python -m fynd.cli stage2 --domain energy
uv run python -m fynd.cli measure-retrieval --as-of 2026-10-20

# Readiness: keys and local replay data are required by the command.
# A cache miss may trigger live requests.
```

### What work belongs here?

Argument parsing, environment loading, client construction, terminal interaction, and writing output files belong to the command boundary. Topic rules, fetching rules, extraction, and metric formulas belong to the modules the command calls. The `search_with` and `embed_with` adapters turn client methods into the plain functions those modules expect.

| Command               | Main input                                       | Main output                                                   |
| --------------------- | ------------------------------------------------ | ------------------------------------------------------------- |
| `stage1`              | Domain                                           | Printed Domain decision                                       |
| `stage2`              | Domain, optional Topic slug and avoidance labels | Offered Topics and optional literature-check decision         |
| `resolve-open-copy`   | DOI                                              | Candidate file locations                                      |
| `fetch-open-copy`     | URL                                              | Download byte count or refusal                                |
| `extract`             | Local file path                                  | Extractor name, page spans, and the first 500 text characters |
| `measure-open-copies` | Seeded Topic and today's Evidence window         | Dated Open copy report and index link                         |
| `build-retrieval-set` | Reference date                                   | Ungraded set JSON under `tests/files/`                        |
| `grade-retrieval-set` | Reference date, optionally `--show`              | Displayed or interactively updated grades                     |
| `measure-retrieval`   | Graded set reference date                        | Ranking metrics and a report under `docs/measurements/`       |

### What gets saved?

The CLI saves grading files and measurement reports, not Projects or Stage state. Interactive grading writes after each accepted answer. Rebuilding a Retrieval set for an existing date replaces that dated file with a new ungraded set, including replacing any grades already in it. Re-running a measurement replaces the report at its dated path and deduplicates its index link.

The measurement paths are relative to the repository, so run these commands from the repository root. External answers and extraction results are cached by the supplied clients and readers. A command's key checks may still require environment settings even when lower-level cache reads would not need a live key.

### What does the retrieval command verify?

The command requires a non-empty, fully graded set with a subject query. It rebuilds the eligible searches using the saved reference date and search limit, then compares returned Paper identifiers with the graded identifiers. A mismatch raises `PoolChanged`. That guard checks identifier membership, not every abstract or the exact original search order.

The current rows are the baseline, individual queries, BM25 label/query comparisons, and dense comparisons at two sizes. Fusion and reranked rows remain issue #37. Tokens reported by Voyage are printed for the run; cache misses can produce live requests.

### Which failures are handled?

`main` prints recognised Stage, model, lookup, and HTTP errors to standard error and exits with status 1. The individual command functions do not handle every possible filesystem or parser error. A numeric grade outside 0–2 currently raises `GradeRefused` past the grading loop, so the command exits instead of reprompting; that reproduced issue is recorded in [bugs.md](../bugs.md). Previously saved grades remain on disk.

## The pieces inside

| Name                                           | What it does                                                                 |
| ---------------------------------------------- | ---------------------------------------------------------------------------- |
| `search_with / embed_with`                     | Adapt real clients to the callable interfaces used by Stage 2 and retrieval. |
| `run_stage_1 / run_stage_2`                    | Offer Domains or Topics and process a supplied Pick.                         |
| `run_resolve_open_copy / run_fetch_open_copy`  | Inspect a DOI’s file candidates or try downloading one URL.                  |
| `run_extract`                                  | Reads a local file, chooses PDF or HTML extraction, and prints a preview.    |
| `run_measure_open_copies`                      | Runs the Seeded Topic’s Open copy pipeline and writes its report.            |
| `run_build_retrieval_set / retrieval_set_path` | Build and locate a dated pool for human grading.                             |
| `run_grade_retrieval_set`                      | Shows or interactively applies grades, saving after each accepted answer.    |
| `PoolChanged / run_measure_retrieval`          | Reject a changed pool and publish metrics for a fully graded dated set.      |
| `main`                                         | Loads .env, parses commands, dispatches work, and reports expected failures. |

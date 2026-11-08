---
id: "measure"
title: "measure.py"
group: "Measurements"
order: 520
source: "src/fynd/measure.py"
summary: "Counts Open copy pipeline outcomes and formats the per-host, per-reason, and per-Paper report."
related: ["open-copy", "reasons", "retrieval-report", "cli"]
note: "The report counts files represented in the retained results, not every intermediate successful download. Actual files and local abstracts are not automatically included in the public repository."
updated: "2026-11-08"
---

## Why this file exists

A failed download should appear in the denominator instead of quietly disappearing. These tables show where Papers fail to become Usable text and whether a rule change helped.

## The flow

1. **Pipeline results**

   Receive each Paper’s outcome and attempted hosts.

2. **Count**

   Summarise links tried, retained files, Usable text, and reasons.

3. **Report**

   Return Markdown; the CLI writes it and updates the measurement index.

## A small example

```text An outcome summary — illustrative
20 Papers attempted
5 reached Usable text
2 runs failed temporarily

The denominator stays 20, not just the successful rows.
```

The caller supplies 18 retained results and `dropped=2` in that example. The denominator is `len(results) + dropped`, not the requested search limit. A search requesting 20 Papers may return fewer than 20; the report describes the Papers actually accounted for.

### What do the three tables count?

| Table     | What one row represents                                                                                 |
| --------- | ------------------------------------------------------------------------------------------------------- |
| By host   | Candidate links attempted at that host, and the extracted-file and usable-text outcomes retained there. |
| By reason | Papers whose retained result has that reason, including zero-count rows.                                |
| By Paper  | One retained result with its year, host, reason, extracted character count, and candidate attempts.     |

```text Illustrative host counts for one Paper
Host A refuses → Host B gives Usable text

Host A: tried 1, files 0, usable 0
Host B: tried 1, files 1, usable 1
Overall: 1 of 1 Papers reached Usable text
```

“Links tried” counts candidate attempts, not HTTP requests or internal retries. “Files received” counts retained results with extracted text, not every file that arrived during intermediate attempts. A host's “Share usable” divides its retained usable count by its candidate-attempt count; the overall percentage uses the Paper denominator.

The report relies on the pipeline's retained host. The mixed refusal/timeout attribution issue recorded in [bugs.md](../bugs.md) can therefore affect its host rows. A zero reason count only means no retained result used that reason; it does not prove a check was never run.

### What happens to missing or failed results?

A Paper with no candidate location remains in the Paper and reason tables, but has no real-host row. A temporarily failed run counted in `dropped` contributes to the overall denominator and explanatory count, but has no per-Paper or reason row because no result was supplied for it.

`share(1, 3)` formats `33%`. `share(0, 0)` returns `-`, since a percentage with no denominator is undefined.

### How does the measurement index stay up to date?

`readme_line` formats a link such as `open-copy-hosts-2026-10-09.md`. `readme_with` appends that exact link only if it is absent. An Open copy report and retrieval report can share a date because their filename prefixes differ. It preserves existing order rather than sorting dates, so callers need to add runs in the desired order.

The optional `previous` and `predicted` parameters add a comparison sentence only when both are supplied. The current CLI leaves them unset. This module returns strings; it does not write files, fetch anything, or read the clock itself.

## The pieces inside

| Name                        | What it does                                                             |
| --------------------------- | ------------------------------------------------------------------------ |
| `readme_line / readme_with` | Build the dated report link and add it once to the measurement index.    |
| `host_of_result`            | Returns the retained result host, or a no-link marker.                   |
| `host_rows`                 | Counts attempted links by host and files/text retained in final results. |
| `reason_counts`             | Counts all configured outcome reasons, including zero counts.            |
| `share`                     | Formats a percentage, or a dash when the denominator is zero.            |
| `report`                    | Formats host, reason, and Paper tables, preserving dropped-run counts.   |

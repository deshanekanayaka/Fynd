---
id: "stages-init"
title: "stages/__init__.py"
group: "Running and checking"
order: 624
source: "src/fynd/stages/__init__.py"
summary: "Marks the Stage package and documents that Stage files contain rules rather than HTTP or saving code."
related: ["stage1", "stage2", "cli"]
updated: "2026-11-08"
---

## Why this file exists

Stage rules need to be reusable from the current CLI and a future runner. The package description records that boundary; the file itself only contains a docstring.

The current modules are `stage1.py` for Domain Picks and `stage2.py` for proposing and checking Topics. Importing this package marker does not run either Stage. Callers supply the external-service functions and handle saving, so the same rules can be exercised from tests and the terminal.

## The flow

1. **Caller**

   CLI today; runner planned.

2. **Stage module**

   Receives values and supplied functions.

3. **Decision**

   Returns a result for the caller to handle.

## A small example

```text Importing Stage rules
from fynd.stages import stage1, stage2
```

## The pieces inside

| Name                | What it does                                                                                    |
| ------------------- | ----------------------------------------------------------------------------------------------- |
| `Package docstring` | Records ADR 0006’s separation of Stage rules from command-line, HTTP, and persistence concerns. |

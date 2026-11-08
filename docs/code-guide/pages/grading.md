---
id: "grading"
title: "grading.py"
group: "Measurements"
order: 518
source: "src/fynd/grading.py"
summary: "Applies human Relevance grades to the Retrieval set and reports what remains ungraded."
related: ["retrieval-set", "retrieval-report", "cli"]
note: "Follow docs/retrieval-set-grading-rule.md: grade the subject, not the country. For the Seeded Topic, 2 means household energy forecasting, 1 means household energy without forecasting, and 0 fails the household gate. The interactive CLI shows cached abstracts; worksheet_rows itself prints titles only."
updated: "2026-11-08"
---

## Why this file exists

Grades must attach to the correct Paper, not a position that changes when a list is reordered. Refusing conflicting overwrites also keeps a disagreement from disappearing silently.

## The flow

1. **Human grade**

   Supply a Paper identifier and grade 0, 1, or 2.

2. **Validate**

   Check membership, grade value, and an existing conflicting grade.

3. **Copy**

   Return an updated copy of the set.

## A small example

```text Grading by identifier
updated = apply_grades(held_set, {"paper-123": 2})
# The original held_set is unchanged.
# Unknown Paper IDs and conflicting existing grades are refused.
```

### Who decides the grade?

The person grading does. These helpers do not call an AI model or inspect the Paper's subject themselves. Follow the [Retrieval set grading rule](retrieval-set-grading-rule.md): for the Seeded Topic, a household-energy forecasting Paper is a 2, household energy without forecasting is a 1, and a Paper outside the household gate is a 0. Country does not decide the grade.

`None` means ungraded; it is different from 0, which is an actual judgement of relevance.

### Why use identifiers and a deep copy?

The input mapping names a Paper by identifier, not its position in the shuffled list. Applying grades in a different dictionary order therefore still updates the right Papers.

All requested changes are checked before any are applied. The function then copies the set and its nested entries, so changing the returned grades does not modify the original set. It does not write a file; the interactive CLI saves the returned set after each accepted answer.

```text Illustrative overwrite rules
Existing grade: None → proposed 2 → accepted
Existing grade: 1    → proposed 1 → accepted; no disagreement
Existing grade: 1    → proposed 2 → GradeRefused
Unknown identifier  → any grade  → GradeRefused
```

### What do the summaries show?

`ungraded` returns the entries still holding `None`. `grade_counts` counts each category present, including `None`; it does not insert zero-count categories. For example, grades `[2, 2, None]` give `{2: 2, None: 1}`.

`worksheet_rows` produces one text row per entry, including its identifier, title, and existing grade. A dot marks an ungraded entry. It preserves saved order and prints no abstract; the interactive CLI separately reads and displays cached abstracts during grading.

## The pieces inside

| Name             | What it does                                                              |
| ---------------- | ------------------------------------------------------------------------- |
| `GradeRefused`   | Raised for an unknown Paper, unsupported grade, or conflicting overwrite. |
| `apply_grades`   | Validates supplied grades and writes them to a deep copy.                 |
| `ungraded`       | Returns entries whose grade is still None.                                |
| `grade_counts`   | Counts entries by grade, including ungraded entries.                      |
| `worksheet_rows` | Formats title-and-identifier rows in the saved shuffled order.            |

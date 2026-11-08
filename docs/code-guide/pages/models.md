---
id: "models"
title: "models.py"
group: "Shared foundations"
order: 1
source: "src/fynd/models.py"
summary: "Defines the Topics, Papers, search responses, and Open copy locations that other files exchange."
related: ["stage2", "semantic-scholar", "openalex", "retrieval"]
note: "Pydantic checks field types; it does not establish that a Paper is relevant or a link contains a file. The legacy names has_open_copy and open_copy_count describe reported links; their naming is still under discussion."
updated: "2026-11-08"
---

## Why this file exists

The search client receives a large API reply, but ranking needs only a Paper’s title, abstract, and identifier. Shared types give both files the same named fields, instead of making each one interpret raw JSON.

## The flow

1. **API or model reply**

   Outside services return JSON.

2. **Named values**

   Clients and Stage 2 create Pydantic models.

3. **Stage or ranking**

   Other code reads fields such as paper.title.

## A small example

```text A Topic created by Stage 2
Topic(
    slug="household-energy-forecasting",
    label="Household energy forecasting",
    query="household electricity demand forecasting",
)
```

`Field(default_factory=list)` gives each SearchResult its own empty list. Missing metadata uses defaults such as an empty abstract or `year=None`.

## The pieces inside

| Name                           | What it does                                                                                  |
| ------------------------------ | --------------------------------------------------------------------------------------------- |
| `Topic`                        | Holds a slug for the Pick, a label for the student, and a query for search.                   |
| `Paper`                        | Holds Semantic Scholar’s paper_id, title, abstract, year, DOI, and reported open link.        |
| `Paper.has_open_copy`          | Checks whether a reported open link is non-empty. It does not download or verify a file.      |
| `SearchResult`                 | Holds the query, the service’s total match count, and the returned Papers.                    |
| `SearchResult.open_copy_count` | Counts returned Papers with reported open links. It does not apply an Evidence window itself. |
| `OpenCopy`                     | Holds a file candidate’s URL, host, and reported licence.                                     |

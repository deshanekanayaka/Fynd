---
id: "openalex"
title: "openalex.py"
group: "External services"
order: 209
source: "src/fynd/openalex.py"
summary: "Looks up a Paper by DOI and returns up to three candidate Open copy file locations."
related: ["models", "contact", "stage2", "open-copy", "cache"]
note: "A candidate is a location to try, not a guaranteed download. The current resolver does not expose or enforce the planned retraction check."
updated: "2026-11-08"
---

## Why this file exists

A Semantic Scholar link can lead to a landing page rather than a file. OpenAlex supplies additional open locations, letting Fynd try repository files before other hosts.

A **DOI** is a digital object identifier for an academic work, such as the illustrative `10.1000/example`. It identifies the Paper rather than naming a particular PDF file. OpenAlex uses that identifier to find metadata describing where copies may be available.

## The flow

1. **DOI**

   Receive the Paper’s digital object identifier.

2. **Open locations**

   Read the cached or live OpenAlex record and filter its locations.

3. **Candidates**

   Return repository-first candidates, or a reason there are none.

## A small example

```text A resolution — illustrative
Resolution(
    found=True,
    candidates=(
        OpenCopy(url="https://repository.example.org/paper.pdf",
                 host="repository.example.org", license="cc-by"),
    ),
)
```

### How are candidate files picked?

1. **Keep locations marked open.**

   Start with OpenAlex's preferred open location, then inspect its other locations. Repeated locations are removed.

2. **Require a PDF link.**

   A landing page alone is not enough. Links on the configured non-file hosts `doi.org`, `dx.doi.org`, and `doaj.org` are excluded.

3. **Order and cap the list.**

   Repository locations come first, followed by other host types. Their original order within each group stays intact. Return at most three candidates.

An explicit licence string is retained when available, but it is not required: the qualifying field is OpenAlex's `is_oa` mark. A candidate may still fail when the downloader tries it.

### What does a lookup return?

| Situation                                | Result                                                          |
| ---------------------------------------- | --------------------------------------------------------------- |
| A record with eligible file locations    | `found=True`, a candidate tuple, and an empty reason            |
| A record with no eligible file locations | `found=True`, no candidates, and a reason such as `no_pdf_link` |
| HTTP 404: no matching record             | `found=False` and `no_openalex_record`                          |
| Another HTTP status, such as 429 or 500  | `WorkNotRead`; nothing is cached                                |

HTTP 200 records and confirmed 404 answers are cached. The filtering rules run on that saved metadata again each time, so changing the candidate rules does not require another external lookup. Cached records have no automatic refresh in this client.

### What happens on a live request?

The request includes the operator's contact email and a User-Agent identifying Fynd. The default HTTP client has a 30-second timeout. Unlike the Semantic Scholar client, this client has no explicit pacing or retry loop; timeout and connection exceptions propagate. Lookup success does not prove a file can be downloaded or that its text will pass the quality checks.

## The pieces inside

| Name                      | What it does                                                                        |
| ------------------------- | ----------------------------------------------------------------------------------- |
| `Resolution`              | Whether the DOI was found, its candidate locations, and a reason if none qualify.   |
| `WorkNotRead / Resolve`   | The lookup failure and the callable interface used by Stage 2 and the pipeline.     |
| `host_of / is_repository` | Reads a URL’s host and checks a location’s repository type.                         |
| `holds_no_file`           | Checks the configured doi.org, dx.doi.org, and doaj.org blocklist.                  |
| `open_locations`          | Collects locations marked open and removes repeated locations.                      |
| `open_candidates`         | Keeps PDF links outside the blocklist, ranks repositories first, and caps at 3.     |
| `reason_for_no_candidate` | Distinguishes no open location, no PDF link, and blocklisted-only candidates.       |
| `OpenAlex.resolve`        | Reads or caches the lookup and converts it into a Resolution.                       |
| `OpenAlex.fetch_work`     | Requests the DOI record. A 404 is cached as not found; other non-200 replies raise. |

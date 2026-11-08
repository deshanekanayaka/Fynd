---
id: "semantic-scholar"
title: "semantic_scholar.py"
group: "External services"
order: 208
source: "src/fynd/semantic_scholar.py"
summary: "Searches Semantic Scholar for Papers and converts the reply into Fynd’s Paper and SearchResult types."
related: ["models", "stage2", "retrieval-set", "cache"]
note: "The search method defaults to 20 results; the Retrieval set builder explicitly requests 50. A reported open link is metadata, not proof of a downloadable file."
updated: "2026-11-08"
---

## Why this file exists

Fynd needs actual academic records behind a Topic. Keeping API details here means Stage 2 can ask for Papers without knowing endpoint URLs, headers, or response field names.

This is a metadata search, not a PDF download. It returns the title, abstract, year, identifiers, and reported open link; OpenAlex and the fetching pipeline handle locating and reading files later.

## The flow

1. **Search words**

   Receive a query, first accepted year, and result limit.

2. **Service or cache**

   Reuse an answer, or make a paced API request.

3. **Papers**

   Return named Paper values inside a SearchResult.

## A small example

```text A normalised Paper — illustrative
API field: externalIds.DOI  →  Paper.doi
API field: openAccessPdf.url → Paper.open_copy_url
Missing abstract            → ""
Missing year                → None
```

### What does a search ask for?

```text Illustrative search inputs
query: household energy forecasting
year_from: 2022
limit: 20

API year filter: 2022-
# Include Papers from 2022 onward, with no explicit ending year.
```

The caller calculates the Evidence window. This client only passes the supplied year range to the service. `SearchResult.total` is the service's reported match count; `len(result.papers)` is how many Papers this response actually contains. A total of 800 with a limit of 20 does not mean Fynd downloaded or read 800 Papers.

### When does it make a request?

The query, result limit, year filter, requested fields, and reply-shape version identify the cache entry. An identical search can reuse its stored reply. Changing the limit from 20 to 50 creates a different entry because the requested answer has changed.

On a cache miss, this client waits until at least one second has passed since its last response. That timing belongs to this client instance; separate instances do not share a rate limiter. The request includes `SEMANTIC_SCHOLAR_API_KEY` when it is set.

### What happens when a request fails?

HTTP 429 means the service is rate limiting the request. The client waits three seconds and tries once more; a second 429 raises `RateLimited`. Other HTTP errors and connection or timeout errors propagate without this retry. No failed request is written to the search cache.

### Why read abstracts from the cache?

Human grading needs Paper abstracts, while ADR 0011 keeps the search replies containing them out of the public repository. `cached_abstracts` reads the available local search entries and returns a dictionary keyed by Paper identifier. Entries without an identifier or abstract are left out, so the grading command can say the abstract is missing. This function makes no network request.

## The pieces inside

| Name                  | What it does                                                             |
| --------------------- | ------------------------------------------------------------------------ |
| `RateLimited`         | Raised after two HTTP 429 responses.                                     |
| `paper_from_api`      | Maps API names and missing values into a Paper.                          |
| `SemanticScholar`     | Keeps an HTTP client, API key, and last-request time.                    |
| `wait_for_rate_limit` | Leaves at least one second between this client’s requests.               |
| `search`              | Caches by query, limit, year range, requested fields, and shape version. |
| `fetch_search`        | Calls the endpoint and retries a 429 once after a wait.                  |
| `cached_abstracts`    | Collects abstracts from locally cached search replies for human grading. |

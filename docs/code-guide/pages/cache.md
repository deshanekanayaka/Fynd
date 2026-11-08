---
id: "cache"
title: "cache.py"
group: "Shared foundations"
order: 2
source: "src/fynd/cache.py"
summary: "Saves external answers and downloaded files on disk so Fynd can reuse work it has already done."
related: ["claude", "semantic-scholar", "voyage", "fetcher", "extract"]
note: "The JSON example omits some real key fields for readability. Writes are not atomic, file size is not a full integrity check, and local disk survival after deployment restarts is not yet designed. Only available replay data can be reused."
updated: "2026-11-08"
---

## Why this file exists

Without the cache, running the same Topic again could repeat searches, download the same PDFs, and pay the AI model again. A cache lets the caller reuse an answer, reducing repeated requests, cost, and waiting. It also lets checks replay recorded answers.

## The flow

1. **Build a key**

   Identify the request by the inputs that affect its answer.

2. **Look on disk**

   A usable entry is a cache hit: reuse it.

3. **Do missing work**

   On a miss, the caller requests or computes an answer and stores it.

## A small example

```text Simplified AI cache entry
{
  "parts": {
    "model": "claude-haiku-4-5",
    "prompt_sha256": "abc123",
    "input_sha256": "def456"
  },
  "value": {
    "topics": [
      {
        "label": "Household energy forecasting",
        "query": "household electricity demand forecasting"
      }
    ]
  }
}
```

### What is actually stored?

| Work          | Cached answer                                        |
| ------------- | ---------------------------------------------------- |
| Paper search  | Titles, abstracts, identifiers, and metadata         |
| AI request    | Generated structured answers                         |
| Embedding     | A list of numbers for one text                       |
| Download      | Bytes in a `.bin` file, with JSON metadata beside it |
| Extraction    | Source text, extractor version, and display spans    |
| Fetch refusal | Status, content type, and reason                     |

The caller decides what is safe to cache. The cache does not make requests itself, and its general JSON writer does not validate a service’s answer.

## The pieces inside

| Name                         | What it does                                                                                  |
| ---------------------------- | --------------------------------------------------------------------------------------------- |
| `CachedBytes`                | A downloaded byte sequence and its content type, such as application/pdf.                     |
| `cache_dir`                  | Finds or creates the cache directory. FYND_CACHE_DIR overrides the default .cache.            |
| `cache_key`                  | Hashes request details into a filename such as claude-<hash>.json.                            |
| `read_file`                  | Reads JSON; missing files and malformed JSON return None.                                     |
| `read / write`               | Loads a stored value or saves it alongside its identifying inputs.                            |
| `bytes_path`                 | Finds the .bin companion file for an entry.                                                   |
| `read_bytes / write_bytes`   | Loads or stores file bytes separately from JSON metadata. Reads check the byte count.         |
| `write_refusal / is_refusal` | Stores and recognises fetch refusals. HTTP 429 is rejected because a rate limit is temporary. |
| `sha256_of`                  | Hashes bytes, for example to identify the input to extraction.                                |
| `read_parts`                 | Returns the recorded inputs so a reader can trace an answer.                                  |

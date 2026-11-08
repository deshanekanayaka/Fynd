---
id: "reasons"
title: "reasons.py"
group: "From Paper to text"
order: 315
source: "src/fynd/reasons.py"
summary: "Defines the shared outcome names used by the Open copy pipeline and its measurement tables."
related: ["openalex", "fetcher", "source-text", "measure"]
updated: "2026-11-08"
---

## Why this file exists

If one file says text_too_short and another invents a different spelling, counts split or disappear. Shared constants give pipeline results and reports the same names.

There are no classes or functions in this file. It names outcomes; the lookup, download, and text-check modules decide which one applies. `Final` marks the values as constants for type checking, but does not enforce immutability at runtime.

## The flow

1. **Pipeline outcome**

   A lookup, fetch, or text check identifies what happened.

2. **Reason constant**

   Return a shared string from this file.

3. **Measurement**

   Count that reason in a predictable table order.

## A small example

```text Examples of shared reasons
USABLE = "usable"
NO_DOI = "no_doi"
ROBOTS_REFUSED = "robots_refused"
TEXT_TOO_SHORT = "text_too_short"
```

For example, a short extracted text makes `source_text.py` return `reasons.TEXT_TOO_SHORT`. The pipeline stores that string on its result, and `measure.py` increments the matching report count.

### What does each outcome mean?

| Value                | Meaning                                                                                                          |
| -------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `usable`             | The extracted text passed the applicable checks.                                                                 |
| `no_doi`             | No DOI was available and the pipeline had no eligible fallback link.                                             |
| `no_openalex_record` | OpenAlex returned no matching record for the DOI.                                                                |
| `no_open_location`   | The record offered no location marked open; also the pipeline's default if the resolver gives no absence reason. |
| `no_pdf_link`        | Open locations exist, but none names a direct PDF link.                                                          |
| `blocklisted_only`   | The available open PDF links all point at configured non-file hosts.                                             |
| `robots_refused`     | The applicable robots decision does not permit the requested download.                                           |
| `fetch_refused`      | The download was rejected, for example by HTTP status, invalid URL, size limit, or redirect limit.               |
| `not_a_pdf`          | The response has neither a PDF content type nor a `%PDF` signature.                                              |
| `text_too_short`     | Extracted text has fewer than 3,000 characters.                                                                  |
| `text_not_textual`   | Fewer than 95% of its characters pass the accepted-character check.                                              |
| `no_section_word`    | Paper text passed the shared checks but contains no configured section-word substring.                           |

### Why is ALL a separate tuple?

`ALL` sets a consistent report order: success first, followed by failures along the pipeline. Reports include a zero-count row for each listed outcome so a reader can compare runs without rows disappearing.

The strings also appear in saved refusals and published reports. When adding an outcome, add its constant to `ALL`, update its producer and walkthrough, and keep report coverage checks current. Temporary failures such as two download timeouts raise exceptions instead of inventing a reason value here; the CLI counts those Papers as dropped.

## The pieces inside

| Name             | What it does                                                                     |
| ---------------- | -------------------------------------------------------------------------------- |
| `Lookup reasons` | no_doi, no_openalex_record, no_open_location, no_pdf_link, and blocklisted_only. |
| `Fetch reasons`  | robots_refused, fetch_refused, and not_a_pdf.                                    |
| `Text reasons`   | text_too_short, text_not_textual, and no_section_word.                           |
| `USABLE`         | Marks text that passed the checks.                                               |
| `ALL`            | Lists the report’s reason order, including reasons whose count is zero.          |

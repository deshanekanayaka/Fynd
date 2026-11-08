---
id: "extract"
title: "extract.py"
group: "From Paper to text"
order: 312
source: "src/fynd/extract.py"
summary: "Turns PDF or HTML bytes into Source text and records which extractor produced it."
related: ["open-copy", "source-text", "cache"]
note: "PDF page spans are offsets into the extracted string, not PDF bytes. The current column heuristic handles up to two columns; scanned pages need OCR, which this code does not provide."
updated: "2026-11-08"
---

## Why this file exists

Later Claims must point to exact characters in a Source text. Keeping the extracted string and display spans gives those future offsets a stable text to refer to.

## The flow

1. **Bytes**

   Receive a downloaded PDF or a saved HTML page.

2. **Read**

   Use pdfplumber for PDF or trafilatura for HTML.

3. **Source text**

   Return the text, extractor version, and PDF page spans; cache the result.

## A small example

```text A page span — illustrative
Source text: "Page one text\n\nPage two text"
Span(kind="page", label="1", start=0, end=13)

text[0:13] == "Page one text"
```

`start` is included and `end` is excluded, matching Python's string slicing. The second page starts after the first page's text plus the two-newline separator. Page spans are for display; they are not extracted Claims or proof that a sentence is supported.

### Why read PDF columns separately?

A two-column Paper can be extracted across the page, mixing a line from the left column with a line from the right. That creates a sentence the author never wrote. This code looks for a **gutter**, the blank vertical strip between columns, and reads down the left side before reading the right.

```text Illustrative reading order
Left column          Right column
A                    C
B                    D

Wanted order: A, B, C, D
Across-page order can mix A with C and B with D.
```

The gutter search examines 33–67% of the page width in 2-point steps and requires a blank band at least 18 points wide, with words on both sides. Points are PDF coordinates, not character positions. If no gap qualifies, the whole page is read without cropping. The page's actual origin is included because its coordinates need not start at zero.

This is a two-column heuristic, not a general layout recogniser. `MAX_COLUMNS=2` matches two crop regions; changing that number alone would not add support for more columns.

### What happens to HTML?

`trafilatura` extracts the main text with tables included and tries to leave out page navigation and other surrounding material. Bytes are passed directly so the library can interpret the declared encoding. No HTML character ranges are recorded, so `structure` is empty. Missing extracted text becomes an empty string, which later quality checks can reject.

### What is cached?

The input-byte hash, extraction path, library name and version, and extraction-shape version identify the entry. The saved result contains the text, extractor identifier, and page spans. Repeating the extraction reuses that result rather than parsing again.

A library upgrade changes the key automatically. Changing Fynd's own extraction rules requires bumping `EXTRACT_SHAPE_VERSION`; otherwise an older extracted string could still be reused. This file makes no network requests and does not run the Usable text checks itself. PDF parser errors propagate to the caller.

## The pieces inside

| Name                                       | What it does                                                                             |
| ------------------------------------------ | ---------------------------------------------------------------------------------------- |
| `Span / Extracted`                         | A labelled range in the text, and the complete text plus extractor metadata.             |
| `Reader`                                   | The callable interface for a byte-to-text reader.                                        |
| `pdf_extractor_name / html_extractor_name` | Record the library name and version.                                                     |
| `crossing_words / words_on_both_sides`     | Help detect a blank vertical gap between columns.                                        |
| `gutter_of`                                | Finds a sufficiently wide gap in the middle third of a PDF page.                         |
| `page_text`                                | Reads left then right when a two-column gutter is found; otherwise reads the page whole. |
| `read_pdf`                                 | Reads pages, joins them with blank lines, and records page character ranges.             |
| `read_html`                                | Extracts text and tables with trafilatura; HTML has no display spans here.               |
| `cached_extraction`                        | Keys results by input-byte hash, extractor version, and output shape.                    |
| `extract_pdf / extract_html`               | The cached entry points used by other files.                                             |

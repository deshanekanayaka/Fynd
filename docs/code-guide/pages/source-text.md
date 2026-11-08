---
id: "source-text"
title: "source_text.py"
group: "From Paper to text"
order: 313
source: "src/fynd/source_text.py"
summary: "Checks whether extracted Source text is readable enough for later Claim extraction."
related: ["extract", "open-copy", "reasons"]
note: "Passing these heuristics does not establish truth or relevance. The 3,000-character minimum also applies to web pages, so a short useful page can fail."
updated: "2026-11-08"
---

## Why this file exists

A download can succeed while its text is a short error page or unreadable characters. These checks stop that text being treated as usable evidence input.

## The flow

1. **Length**

   Require at least 3,000 characters.

2. **Characters**

   Require at least 95% ordinary characters.

3. **Paper check**

   For Papers only, require a configured section word.

## A small example

```text A text-quality decision
reason_against_page_text("Access denied")
# "text_too_short"

# Passing text returns "" (an empty reason).
# Paper text must also contain a word such as "method" or "results".
```

### What counts as an ordinary character?

Unicode letters and digits, whitespace, and the punctuation listed in `ORDINARY_PUNCTUATION` count toward the accepted share. This is not a dictionary check or an English-language detector. A word can be meaningless and still contain ordinary characters.

```text Illustrative 95% boundary
10,000 characters in total
9,500 accepted characters + 500 unrecognised glyphs → passes
9,499 accepted characters + 501 unrecognised glyphs → text_not_textual
```

### What is different for Papers?

Both Paper and web-page text need at least 3,000 characters and an ordinary share of at least 0.95. Paper text also needs a substring such as `abstract`, `method`, or `results`, ignoring case. For example, `methodology` contains `method` and passes that part of the check. No actual heading is required.

The function returns only the first failure: length, then character share, then the Paper-specific section check. An empty string means no check failed; it does not mean the Source text is empty. The same length minimum applies to web pages, even if a shorter page would be useful.

### Why keep the extracted text unchanged?

Later Claims must point to exact characters in the saved Source text. These functions inspect the string and return a reason; they do not clean or rewrite it, so they do not move offsets.

The thresholds were motivated by the first [Open copy measurement](measurements/open-copy-hosts-2026-10-09.md), not an independent accuracy evaluation of this filter. Passing is a useful extraction check, not proof that the text is relevant, factually correct, or in the author's intended reading order.

## The pieces inside

| Name                                   | What it does                                                                |
| -------------------------------------- | --------------------------------------------------------------------------- |
| `MIN_CHARACTERS / MIN_ORDINARY_SHARE`  | The current thresholds: 3,000 characters and 0.95 ordinary share.           |
| `ORDINARY_PUNCTUATION / SECTION_WORDS` | Accepted punctuation and the section words used for Paper text.             |
| `is_ordinary / ordinary_share`         | Classify characters and calculate the readable-character share.             |
| `has_a_section_word`                   | Checks for a section-word substring; it does not recognise actual headings. |
| `reason_against_text`                  | Runs the shared length and character checks.                                |
| `reason_against_paper_text`            | Adds the section-word check for Papers.                                     |
| `reason_against_page_text`             | Uses only the shared checks for web pages.                                  |

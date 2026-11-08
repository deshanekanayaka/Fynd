---
id: "fetcher"
title: "fetcher.py"
group: "From Paper to text"
order: 311
source: "src/fynd/fetcher.py"
summary: "Downloads candidate PDF files while checking robots.txt, pacing requests, and limiting download size."
related: ["contact", "open-copy", "cache", "reasons"]
note: "This downloader accepts PDFs. HTML extraction exists separately, but a general Stage 3 web-page fetching path is not complete. A PDF content type or %PDF prefix passes the initial check; successful parsing and text checks happen later."
updated: "2026-11-08"
---

## Why this file exists

A file URL can return a refusal, a login page, an oversized body, or no answer. This file turns those outcomes into clear results instead of treating every response as a usable PDF.

## The flow

1. **Permission**

   Check the host’s robots.txt before using cached bytes or fetching.

2. **Download**

   Apply host delays, timeout, redirect limit, and a 20 MiB body cap.

3. **Result**

   Return Fetched bytes, a Refused reason, or raise after repeated temporary failures.

## A small example

```text Three different outcomes
Fetched(data=b"%PDF...", content_type="application/pdf")
Refused(status=403, content_type="text/html", reason="fetch_refused")
FetchFailed(...)  # e.g. two timeouts; not stored as a stable refusal
```

### What is robots.txt?

It is a host's text file describing which paths automated clients may access. For `https://repository.example.org/paper.pdf`, Fynd first asks for `https://repository.example.org/robots.txt` and checks the rules against Fynd's User-Agent.

```text Illustrative robots rules
User-agent: *
Disallow: /private/
Crawl-delay: 5

# /paper.pdf is allowed; /private/paper.pdf is refused.
# This host asks for a five-second gap between requests.
```

For robots responses, HTTP 200 is parsed. A 4xx other than 429 permits access under the current policy. HTTP 429, server errors, and transport failures refuse access for this client run without saving that failure as a disk-cached policy. This robots lookup has no retry loop of its own.

### What are the actual limits?

| Setting               | Value            | Meaning                                                                                           |
| --------------------- | ---------------- | ------------------------------------------------------------------------------------------------- |
| Minimum request gap   | 1 second         | Wait the remaining gap after a host's last response. Different hosts have separate timers.        |
| Crawl delay           | Up to 10 seconds | Use the larger of 1 second and the parsed host delay. Skip hosts asking for more than 10 seconds. |
| Retry wait            | 3 seconds        | Wait before the one download retry after a rate limit or transport failure.                       |
| HTTP timeout          | 30 seconds       | Configures HTTPX network timeouts; it is not a total Stage deadline.                              |
| Redirects             | 3                | Refuse a chain requiring more redirects.                                                          |
| Download size         | 20 MiB           | Refuse an oversized response instead of caching a partial PDF.                                    |
| Robots text retained  | 500 KiB          | Limit how much of the rules file is parsed.                                                       |
| Robots disk-cache age | 24 hours         | Refresh older disk entries; in-memory rules are reused for the lifetime of this client.           |

The standard-library robots parser reads whole-number Crawl-delay values. Fractional values such as `0.5` are ignored; Fynd's one-second minimum still applies.

### Why distinguish a refusal from a failure?

A file's HTTP 403 becomes a `Refused` result that the pipeline can count and cache. A timeout or HTTP 429 may be temporary, so a download gets one retry after three seconds. A second temporary failure raises `FetchFailed` and leaves no file-cache answer. Download refusals do not have an automatic expiry here.

A robots refusal stays out of the file cache because permissions have a separate cache. Applicable robots rules are checked before reusing file bytes. A content type of `application/pdf` **or** a `%PDF` byte prefix passes the initial format check; neither establishes that extraction will succeed.

### Existing boundaries still to fix

Two cases were reproduced with fake HTTP responses during this review. The in-memory robots cache uses only the host, so HTTP rules can be reused for HTTPS on the same host even though the disk cache distinguishes schemes. Also, HTTPX follows download redirects automatically; the redirected destination does not get an independent robots or pacing check. These are recorded in `bugs.md` and were not changed in this readability pass.

## The pieces inside

| Name                                          | What it does                                                                     |
| --------------------------------------------- | -------------------------------------------------------------------------------- |
| `Fetched / Refused / FetchAnswer`             | Represent downloaded bytes or a recorded refusal.                                |
| `FetchFailed`                                 | Raised after repeated transport failures or rate limits.                         |
| `Robots / Robots.allows`                      | Hold and apply a host’s permission rules and crawl delay.                        |
| `robots_url_of / is_fetchable`                | Build the robots.txt address and check for an HTTP(S) URL with a host.           |
| `robots_from`                                 | Parses robots replies into permission and delay decisions.                       |
| `looks_like_a_pdf / host_of`                  | Check the PDF content type or signature and read the URL host.                   |
| `Fetcher.fetch`                               | Checks permissions, reads the fetch cache, then downloads and caches an outcome. |
| `robots_for / robots_is_stale / fetch_robots` | Read robots rules, with a 24-hour disk-cache lifetime for eligible responses.    |
| `wait_seconds_for / wait_for_host`            | Respect the configured host delay before requests.                               |
| `fetch_body / read_one_response`              | Retry temporary failures and stream the response under the size cap.             |

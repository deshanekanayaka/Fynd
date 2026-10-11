---
status: accepted
date: 2026-10-11
---

# An open file is a licence question, and not a host question

Fynd fetches any location that OpenAlex marks as open and that names a PDF link, whatever kind of host it sits on. A repository ranks first and a journal second. A short blocklist of hosts that hold no file is the only host rule that stays. This supersedes one rule of [ADR 0007](./0007-the-open-copy-is-resolved-then-measured.md), which accepted a location only when OpenAlex called its source a repository.

## The fact that forced this

The live run of 2026-10-09 fetched 20 Papers of the Seeded Topic and reached Usable text for 5. The 20 cached OpenAlex records say what the pipeline left on the table.

| What the records say | Papers |
|---|---|
| No open location at all, so the Paper is closed | 6 |
| At least one open location with a PDF link | 11 |
| An open location, but every one of them is a landing page | 3 |

One of the 11 names a single PDF link on doi.org, which holds no file. So 10 Papers carry a free file on a host Fynd can fetch, and the pipeline reached 5.

The gate walls cost 6 Papers. The repository rule costs 5 more. The 7 open PDF links it refuses sit on `www.mdpi.com`, `journals.plos.org`, `www.sciencedirect.com`, `pdpublishers.com` and `www.ijspe.com`, and OpenAlex states a `cc-by` licence for 5 of the 7.

## The decision

An open file is a licence question. OpenAlex marks a location `is_oa` and states the licence, and that mark is the test Fynd applies. The host decides nothing.

A candidate is any open location that names a PDF link and whose host is not on the blocklist. Candidates rank with a repository first and a journal second, and inside one rank they keep the order OpenAlex returned, so `best_oa_location` stays first. Fynd tries at most 3 candidates and stops at the first file.

Usable text ends the attempts, and a file alone does not. The candidates of one Paper are three files of one article, and the usable text checks test the file. A scan of paper pages extracts to nonsense, and the next candidate can be a born digital file that extracts cleanly. The cost is one extra fetch for a Paper that already failed a check, which was 0 Papers of 20 on 2026-10-09. A file that failed a check is still the Paper's answer when no later candidate gives better, and it beats a refusal that came after it, because the pipeline got one step further with the file.

The blocklist holds one kind of entry, which is a host that holds no file by design. Three hosts are on it today, each with the reason that measured it.

| Host | Why it holds no file |
|---|---|
| doi.org | A redirect to a publisher page. 6 of 12 links in the day 1 pool, and 1 PDF link in the day 4 pool. |
| dx.doi.org | The older name of the same service. |
| doaj.org | An index of journals, and not a file host. 2 refusals with a 403 in the run of 2026-10-09. |

A host that refused once is not listed. The fetch cache already holds its status, the measurement table already counts it, and a dated list of refusals in the source code needs a human to edit it after every run.

Fynd reads robots.txt before the first fetch to a host and obeys it, under RFC 9309. A 404, and any other 4xx but a rate limit, allows everything. A 5xx, a rate limit and a timeout allow nothing on that host for this run, and none of those answers is cached, so one bad day at one university does not wall that host off for ever. The user agent the rules match against is the user agent Fynd sends, which names the repository and the operator.

The check runs before the fetch cache, so a path a host disallows is refused even when an earlier run already holds its bytes. A published table must not count a file Fynd may no longer ask for.

A stored robots answer is read again after one day, which is the limit RFC 9309 names, because a repository that adds a rule next week must win over a file Fynd read today. The body is capped at 500 kibibytes, which is the size that standard asks a crawler to read. A redirect chain that never ends counts as unreachable, with a timeout and a 5xx and a rate limit. A link with no host or with a scheme that is not http or https is never fetched, because such a link would share one robots answer with every other one, and the rules of one host must never govern another.

`urllib.robotparser` from the standard library matches the rules, and Fynd fetches the file itself, so the timeout, the cache and the user agent stay Fynd's own. Two differences are worth knowing. That module is not a certified RFC 9309 implementation, and it reads a whole number `Crawl-delay` and ignores a fractional one, so `Crawl-delay: 0.5` reads as no delay and Fynd then waits its own one second, which is longer.

Fynd waits the larger of one second and a named `Crawl-delay`, up to 10 seconds. A longer delay skips that host, because 30 seconds for each file is 10 minutes over 20 Papers. A robots refusal spends one of the 3 attempts, so a Paper whose every candidate is disallowed records 3 attempts and the reason `robots_refused`.

The Semantic Scholar link survives as the last resort, and only when OpenAlex names no candidate at all. It produced none of the 5 usable files of the run of 2026-10-09 and cost 3 refused fetches, but it is the only path for a Paper with no digital object identifier, which was 2 of 20 Papers in the day 1 pool. It passes the same blocklist.

## Why a publisher is still not fetched blind

Fynd fetches a journal file because OpenAlex marked it open, and never because a link ends in `.pdf`. A request to a publisher page that nothing marked open is refused even though the answer would be thrown away, for three reasons.

A paywall answers with a page and not with an error. Elsevier returns a cookie notice or a login form with a status of 200. ADR 0007 names the real cost of that: a Claim located in a cookie notice passes the citation guard, and the citation guard is the one promise this product makes.

A blind fetch spends the operator's name. Every request carries Deshan's address and a link to a public repository. A pattern of requests for files the sender has no right to is the pattern that gets an address blocked, and 9 university hosts in this pool answer the same program.

The cost of the refusal is countable, and it is small. A Paper that is open at a publisher and marked open gets fetched under this record. A Paper that is open nowhere is 6 of 20, and no rule reaches it.

## Consequences

The predicted yield is 10 Papers with a file against 5 today, and the run of issue 19 says what really happened.

The reason vocabulary changes, because the old names say host things. `no_repository_location` becomes `no_open_location`, for a Paper that OpenAlex marks open nowhere. `no_pdf_link` joins it, for a Paper whose open locations are all landing pages. `blocklisted_only` joins it, for a Paper whose every open PDF link sits on the blocklist. `robots_refused` joins it, and it stays apart from `fetch_refused`, because a 403 and a disallowed path say different things about a host. The reason table prints them in pipeline order, which is the order the pipeline reaches them.

The stage 2 gate counts a different thing. See the note of 2026-10-11 in [ADR 0002](./0002-topics-are-generated-then-verified.md).

The measurement table of 2026-10-09 keeps the names it was written with. Every later run writes its own dated file in `docs/measurements`, and a `README.md` there lists the runs in order.

`CONTEXT.md` now defines an Open copy by its licence and not by its host.

## Considered options

Keep the repository rule and add Europe PMC and CORE as extra indexes. Rejected for now. Both are a day of work each, and the measured records say the free file is already named in a record Fynd holds. Spend the day only if the new number is still short.

Accept an open location only when OpenAlex states a licence. Rejected. 4 of the 18 open PDF links state no licence, including `eprints.whiterose.ac.uk`, which gave 75,457 characters of Usable text for Paper 3. The `is_oa` mark is the field that means free, and the licence field is often empty for a file that is plainly free.

Keep a list of publisher hosts that are refused even when OpenAlex marks the file open. Rejected, because that is the rule this record reverses, and `www.mdpi.com` with a `cc-by` PDF is the case that shows it wrong.

Follow a landing page to its file with the `citation_pdf_url` meta tag. Deferred, and issue 16 is closed with this number: the 3 landing-page-only Papers of this pool name doi.org three times and doaj.org once. Both are on the blocklist, so the hop would pay 0 Papers today and would need a fetch of the one host that holds no file. The hop returns to the table when a measured run shows a landing-page-only Paper on a repository host.

Try every candidate instead of 3. Rejected for now. 19 of the 20 Papers hold 3 or fewer candidates, so the cap binds once. The attempts column in the next measurement says whether the fourth attempt would have paid.

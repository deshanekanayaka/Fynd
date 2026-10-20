# Bugs

Log of real bugs found during development. Each entry holds the root cause, the fix, the verification, and how the same class of bug stays away. Newest first.

A bug a code review found before anyone ran the code is still a bug. The mistake is the same, and only the cost is smaller.

---

## A request parameter the SDK had removed

**Found:** 2026-10-20, by the first live stage 2 run, on branch `send-no-temperature`.

**What happened:**

`uv run python -m fynd.cli stage2 --domain energy` stopped with a `TypeError`.

```
TypeError: Messages.create() got an unexpected keyword argument 'temperature'
```

`src/fynd/claude.py` sent `temperature=0` on every model call, because ADR 0004 asked for fixed decoding. The Anthropic SDK has removed every sampling parameter. `messages.create` in version 1.12.1 accepts no `temperature`, no `top_p` and no `top_k`, so the call failed before any request left the machine.

Stage 2 had never run live. 198 tests passed, the command had never asked a model anything, and `pyproject.toml` allows `anthropic>=1.12.1`, so the installed version was always going to be one that refuses the argument.

**Root cause:** the test fakes the SDK at the client boundary. `tests/test_claude.py` replaces `fynd.claude.anthropic.Anthropic` with a fake whose `create(**kwargs)` accepts anything, so it asserted that `temperature` was 0 in the arguments and could never learn that the real method takes no such argument. A fake that accepts every keyword cannot fail on a keyword the real one dropped.

**Fix:** the request sends no decoding parameter, and the cache key names none, because a key that names a value the request does not carry lies to the next reader. ADR 0004 keeps its decision and carries a dated note that says the replay promise now rests on the cache alone.

**Verification:** `tests/test_claude.py` asserts that the arguments hold no `temperature`, no `top_p` and no `top_k`. The live stage 2 run then returned Topics.

**Prevention:** a test that fakes an outside library cannot check that library's signature, so the first live run of a command is part of the work and not a later step. This is the second finding from a first live run, after the cap that silently dropped Papers from the Retrieval set. Both were invisible to a green suite. When a ticket adds a command, run it once against the real service before the ticket closes, and write down what the run returned.

---

## A published number nobody checked against the file it came from

**Found:** 2026-10-20, by a code review of branch `build-the-retrieval-set`, before a merge to `main`.

**What happened:**

`docs/retrieval-set-grading-rule.md` said "Three such Papers reached the measured pool of 2026-10-17". `NEXT-STEPS.md` said "3 of the 20 Papers are about ultra-processed food" in six places, from day 4 onward.

The count is 2. `docs/measurements/open-copy-hosts-2026-10-17.md` holds two such Papers, `docs/measurements/open-copy-hosts-2026-10-09.md` holds two, and `tests/files/pool-2026-10-09.json` holds two. No file anywhere holds three.

The wrong number then travelled. It reached the spec of issue 30, the argument for branch A over branch B in the day 8 entry, and the new grading rule, each time as a fact that justified a decision.

**Root cause:** the number was read once by eye and then copied by hand. No command produced it, and nobody opened the table again before repeating it. `AGENTS.md` states the rule that a published number comes from a command anyone runs, and this number never had one.

**Fix:** every copy in `NEXT-STEPS.md` says 2, the grading rule says 2, and a dated section in `NEXT-STEPS.md` records the correction so the old number is not a mystery to the next reader. The finding behind the number does not change, because a search returning 2 food Papers for an energy Topic is still imprecise.

**Verification:** `grep -ci ultra docs/measurements/open-copy-hosts-2026-10-17.md` returns 2, and so does the same count over the 2026-10-09 table and the committed pool file. The retrieval table of issue 34 replaces the hand count with a graded number, which is what the Retrieval set exists for.

**Prevention:** before a document repeats a count, run the count. A number in prose that no command produces is a claim, and this repository already says so. The rule now has a second case behind it, which is that a number which justifies a decision gets checked at the moment it is reused, and not only at the moment it is written.

---

## A fixed comparison number stays wrong on every later run

**Found:** 2026-10-17, by a code review of branch `record-day-6`, before a merge to `main`.

**What happened:**

Issue 19 asked the measurement file to name the previous count, the prediction, and the new count. The first draft added two constants to `src/fynd/cli.py`:

```python
PREVIOUS_USABLE = 5
PREDICTED_USABLE = 10
```

`run_measure_open_copies` passed both to `report()` on every call. Those two numbers are the count from the run of 2026-10-09 and the prediction ADR 0012 made for the run after it. Neither number has a reader that moves it forward.

Take a run on 2026-11-20. It writes the same sentence as this run, "The previous run reached 5 of 20 Papers. The rule fix predicted 10." The real previous run is the one from 2026-10-17 by then, and nobody made a new prediction for it.

**Root cause:** a fact about one comparison, between two named dates, sat as a constant of the command. It belongs instead as a line in the one file that comparison produced. The command runs again next month. The constant does not know that.

**Fix:** the two constants and the `previous=`/`predicted=` arguments leave `cli.py`. `measure.report()` keeps the optional `previous` and `predicted` parameters. A later issue can ask for a comparison again, and no caller passes them today. The one sentence this issue needed stays as plain text, already written into `docs/measurements/open-copy-hosts-2026-10-17.md`. The code can change, and that file stays as it was written.

**Verification:** `tests/test_cli.py` asserts that `src/fynd/cli.py` holds no `previous=` or `predicted=` keyword argument. With both arguments left at `None`, `report()` prints no comparison line, and `tests/test_measure.py` already asserts that.

**Prevention:**

- A number that compares two runs by date is a fact about one occasion, and not a setting of the command. Write it into the file that occasion produced. Do not write it into a constant the command carries forward.
- Ask one question of every module level constant: what reader moves this value, and on what event? A constant with no such reader is a fact dressed as a setting.

---

## One failed OpenAlex lookup broke the whole Stage

**Found:** 2026-10-16, by a code review of branch `issue-18-stage-2-gate-counts-candidates`, before a merge to `main`.

**What happened:**

The stage 2 gate now asks OpenAlex about every Paper of the search, and counts the Papers that name a file Fynd may fetch:

```python
for paper in result.papers:
    if not paper.doi:
        continue
    if resolve(paper.doi).candidates:
        count += 1
```

`OpenAlex.fetch_work` raises `WorkNotRead` for every status that is not 200 and not 404. A 503 from OpenAlex, or a 429, therefore left `count_papers_with_a_candidate`, left `accept_topic`, and ended the Stage.

Here is the cost in one example. The search returns 20 Papers. The first 14 resolve, and 6 of them already hold a candidate, which is twice the threshold of 3. The 15th identifier gets a 503. The student gets no decision at all, although the answer was decided five Papers earlier.

**Root cause:** the new code treated a transport failure as a reason to stop. ADR 0006 says that `accept` returns what it decided and does not raise for a normal outcome. A remote service that answers 503 is a normal outcome for a gate that makes 20 calls.

**Fix:** the loop catches `WorkNotRead` and skips that Paper. A Paper Fynd could not ask about is a Paper it cannot promise, so the count errs low, which is what the gate already does for a Paper with no digital object identifier.

**Verification:** a test passes a lookup that raises `WorkNotRead` for one identifier of four. It asserts the answer is `TopicKept` with a count of 3.

**Prevention:**

- A function that calls a remote service once for each item of a pool needs one guard for each item. The same lesson is in the robots.txt entry below, and this is the second time a loop over 20 Papers lost all 20 to one of them.
- Read the error classes of the function you call before you call it in a loop. `resolve` reads the cache first, which hides how often it reaches the network.
- A Stage returns a decision. When a new argument can raise, the Stage needs a rule for that failure, written at the same time as the argument.

---

## The missing contact address was found after the money was spent

**Found:** 2026-10-16, by the same code review.

**What happened:**

`run_stage_2` guards one variable before it does any work:

```python
if not os.environ.get("ANTHROPIC_API_KEY"):
    raise SystemExit(...)
```

The gate now calls OpenAlex, and every outbound request names a human through `contact_email()`, which raises `ContactEmailMissing` when `FYND_CONTACT_EMAIL` is absent. Stage 2 never needed that address before, because Semantic Scholar does not read it.

So a student with the model key set and no contact address paid for the model call that proposes 10 Topics, paid for the search, and then stopped at the first uncached identifier with no decision. The command line prints the right sentence, because `ContactEmailMissing` is caught at the edge. The sentence just arrives after the cost.

**Root cause:** the guard list at the top of a command is a copy of what that command needed on the day it was written. A new call inside a Stage added a new requirement, and nothing connects the two.

**Fix:** `run_stage_2` calls `contact_email()` before the model call. The call raises the same exception with the same sentence, and the edge still catches it.

**Verification:** a read of `run_stage_2`, where the check now sits above the model call. No test covers it, because the guard is one line at the edge, and `tests/test_openalex.py` already holds a test that the lookup raises `ContactEmailMissing` with no address set.

**Prevention:**

- When a Stage gains a new outside call, read the environment that call needs, and check it where the command starts.
- A check that costs nothing belongs before a call that costs money. The order of the two guards is the whole fix.

---

## A docstring named a measurement file that does not exist yet

**Found:** 2026-10-16, by the same code review.

**What happened:**

The docstring of `SearchResult.open_copy_count` was rewritten to say that no gate reads the field any more, and it added this:

> the measurement files quote it beside the count the stage 2 gate uses

`docs/measurements/open-copy-hosts.md` is the only measurement file today, and it quotes neither number. It reports Usable text by host and by reason. The sentence becomes true after the live run of issue 19, and a reader who follows it today finds nothing.

**Root cause:** the sentence described the plan and not the repository. The design round of day 5 settled that the measurement files quote both numbers, and the docstring copied the decision as if it were already done.

**Fix:** the docstring now says what the field is and what the gate counts instead, with the two numbers of the pool of 2026-10-09, and it names no file.

**Verification:** a read of `docs/measurements/open-copy-hosts.md`.

**Prevention:**

- A docstring states what is true in this commit. A plan goes in `NEXT-STEPS.md`, where a date and an issue number carry it.
- A cross reference to a file is a promise that a reader will check. Open the file before you name it.

---

## A test name said stage 2 reads a field it had just stopped reading

**Found:** 2026-10-16, by the same code review.

**What happened:**

`tests/test_semantic_scholar.py` held this name:

```python
def test_the_open_copy_count_is_what_stage_2_reads(tmp_path, monkeypatch) -> None:
```

The assertion inside it is still right, because the field still counts the Papers with a link. The name is now the opposite of the truth, and `models.py` states the truth three files away: "No gate reads this number."

The next reader greps for what the gate reads, finds this name, and trusts it. A test name is read far more often than the two lines under it.

**Root cause:** the change moved the rule out of one file and left the name that described the old rule in another file. Nothing fails when a name goes stale.

**Fix:** the test is now `test_the_open_copy_count_counts_the_papers_with_a_link`, with a comment that says the stage 2 gate stopped reading it.

**Verification:** a search for `stage_2_reads` across the repository returns nothing.

**Prevention:**

- When a rule moves, grep for the words of the old rule and not only for the names of the functions. A name in a test is documentation that no compiler checks.
- A behaviour the code no longer has must not survive as a test name, because a name outlives the memory of the change.

---

## A redirect loop on robots.txt ends the whole measurement run

**Found:** 2026-10-11, by a code review of branch `read-and-obey-robots-txt`, before a merge to `main`.

**What happened:**

`fetch_robots` in `src/fynd/fetcher.py` asks a host for its robots.txt and catches two kinds of failure:

```python
except (httpx.TimeoutException, httpx.TransportError):
    return 0, "", False
```

A robots.txt address that redirects in a loop raises a third kind, `httpx.TooManyRedirects`. That class sits under `httpx.RequestError` and not under `httpx.TransportError`, so neither name in the tuple matches it.

The error then leaves `Fetcher.fetch`, passes `read_open_copy`, which catches only `FetchFailed`, and passes `run_measure_open_copies`, which catches `WorkNotRead` and `FetchFailed`. The command stops on that Paper with a traceback and loses every Paper after it. The client follows 3 redirects, which is a limit tuned for a PDF. RFC 9309 asks a crawler to follow at least 5 for a robots.txt, so an ordinary chain of http to https to www trips it.

**Root cause:** the `except` tuple came from memory and not from the exception tree of the library. The file fetch catches `TooManyRedirects` by name a few lines below, so the two paths through one file disagreed.

**Fix:** `httpx.TooManyRedirects` joins the tuple, and it maps to the answer the other two map to, which is "no answer, and nothing cached". A host that answers nothing is asked again on the next run.

**Verification:** a test raises the real class from a mock transport and asserts the fetch returns `robots_refused` and asks for no file. The reviewer reproduced the old behaviour first, as `RAISED httpx.TooManyRedirects` out of `Fetcher.fetch`.

**Prevention:**

- Catch by the exception tree of the library and not by the two names you remember. `httpx.TransportError` and `httpx.RequestError` are different branches, and only one of them covers a redirect loop.
- A command that loops over a pool of 20 needs one guard for each item, so one bad item costs one item. The measurement already drops a Paper on a named failure, and the new class walked around that design.

---

## A rate limit on robots.txt was stored, which blocked that host for ever

**Found:** 2026-10-11, by the same code review.

**What happened:**

A host that answers a robots.txt request with 429 is asking Fynd to come back later. `fetch_robots` decided what to store with one test:

```python
answered = 400 <= status < 500
```

429 passes that test, so the answer went to disk as `{"status": 429, "text": ""}`. On every later run, `robots_from` reads a stored 429 and returns `refuse_all`, because a rate limit says nothing about what a host permits. Nothing in `cache.py` expires an entry, so that host stays refused for ever.

The module comment, the docstring of `robots_for` and ADR 0012 all say that a rate limit is never cached. Only the code disagreed, and no test covered 429. The one test for an uncached answer used 500.

**Root cause:** the cache module already holds this rule. `cache.write_refusal` refuses to store a 429 through its `UNCACHEABLE_STATUS` guard. The robots path called `cache.write` instead and walked around the guard, so one rule lived in two places and only one of them was right.

**Fix:** the test is now `400 <= status < 500 and status != RATE_LIMIT_STATUS`, which matches RFC 9309, where a 429 sits with the 5xx answers as unreachable.

**Verification:** a test answers robots.txt with 429 on the first run and with a permissive file on the second. It asserts that the second run fetches the PDF. The reviewer reproduced the old behaviour, including the name of the cache file it wrote.

**Prevention:**

- A status that means "ask again later" is never cacheable. That rule belongs inside the cache module, where `UNCACHEABLE_STATUS` already states it, and not in each caller.
- A second write path around an existing guard is the shape to watch for. The guard was load bearing and the new code did not use it.
- Where a docstring and the code disagree, the missing thing is a test. Three comments stated the rule the code broke.

---

## The robots.txt rules never expired, so a new rule never won

**Found:** 2026-10-11, by the same code review.

**What happened:**

`robots_for` returned a stored answer whenever the file existed. Nothing in `cache.py` records a time, and a search for `ttl`, `expire` and `max_age` across `src/` returns nothing. So Fynd read `dro.dur.ac.uk/robots.txt` once and obeyed that copy for ever. A repository that adds `Disallow: /` next week never won. The only way to read the file again was to delete the cache directory by hand.

A comment in `fetch` claimed the opposite, which is that a rule the host changes must win.

**Root cause:** every other entry in this cache is keyed by a hash of its own input. New input makes a new key, so an old entry is never asked for again. robots.txt is the first entry keyed by an address, where the content behind one key changes over time. The cache had no answer for that case, and the code assumed the old one.

**Fix:** the stored value carries `read_at`, and `robots_is_stale` compares it against `ROBOTS_MAX_AGE_SECONDS`, which is 24 hours, the limit RFC 9309 names. A stale entry is read again from the host and written back with a new time.

**Verification:** a test stores a permissive file and moves `time.time` past one day. It asserts that the second fetcher asks the host again and obeys a new `Disallow`. The first draft of that test failed for its own reason, which taught something: it set an absolute clock value in the past, so the entry read as fresh. The stored time is a real wall clock time, and a test moves the clock forward from it.

**Prevention:**

- Every cache entry needs an answer to one question, which is how long its answer stays true. An entry keyed by a hash of its input is true for ever. An entry keyed by an address has a lifetime, so store the time beside the value.
- A cache with no expiry is a decision. Write it down, or take the limit the standard names.

---

## The robots.txt body had no size cap

**Found:** 2026-10-11, by the same code review.

**What happened:**

The file fetch streams a response and stops at `MAX_BYTES`, which is 20 megabytes. The robots.txt fetch called `self.client.get(...)`, which buffers the whole body into memory before any code sees it. It then ran `splitlines()` over all of it. A host that serves a megabyte at `/robots.txt`, or redirects that path to a large file, was read in full. The reviewer reproduced a 5 megabyte body passing through.

**Root cause:** the limits of this file live in the method that already existed. The new method copied the shape of a fetch and not its three limits.

**Fix:** `fetch_robots` reads through `client.stream` and stops at `ROBOTS_MAX_BYTES`, which is 500 kibibytes, the size RFC 9309 asks a crawler to read. The bytes decode as UTF-8 with replacement, because a rules file with one bad byte is still a rules file.

**Verification:** a test serves a body larger than the cap and asserts the fetch still succeeds and the PDF arrives. Stated honestly, that test proves the read completes and the cut happens, and it does not prove a memory limit under a hostile host.

**Prevention:**

- Every network read needs three limits, which are a size cap, a timeout and a redirect cap. A buffered `client.get` has no size cap at all, so a capped read is a stream plus a counter.
- When you add a second call to a module that already makes one, copy its limits and not only its shape.

---

## A link with no host shared one robots answer with every other such link

**Found:** 2026-10-11, by the same code review.

**What happened:**

`host_of` returns `urlparse(url).netloc`, which is the empty string for a link such as `dro.dur.ac.uk/a.pdf`, with no scheme in front. The robots cache key held that host, so every link with no scheme shared one entry. The rules of one host then governed another. The request itself also crashed, because `robots_url_of` built the address `https:///robots.txt`, and `httpx` raised `ValueError: unknown url type: '/robots.txt'`, which no handler catches.

The key also left the scheme out. RFC 9309 scopes a rules file to one scheme and one host, so `http` and `https` shared one entry as well.

**Root cause:** the fetcher trusted the shape of its input. OpenAlex returns absolute addresses today, so the case never arrived, and the code read a value it never tested.

**Fix:** `is_fetchable(url)` demands a scheme of http or https and a host that is not empty. `Fetcher.fetch` refuses anything else before it reads robots.txt, with the reason the table counts. The robots key now holds the scheme and the host.

**Verification:** a test fetches a link with no scheme and asserts a refusal with no request made. The full suite stays green, which shows no caller depended on the old behaviour.

**Prevention:**

- Check a value once, at the boundary where it enters your own rules, and let everything after that point trust it.
- An empty key is a shared key, and a shared key merges two things in silence. The identity of a cache entry belongs in its key and never in the caller's head.

---

## The host table hid the refusals it exists to show

**Found:** 2026-10-11, by a code review of branch `accept-every-open-location-with-a-pdf-link`, before a merge to `main`.

**What happened:**

ADR 0012 let one Paper try up to three links. `host_rows` in `src/fynd/measure.py` still added one link for each Paper. It took the host from `result.open_copy`, which is the link that answered or the last link tried.

So a Paper refused at `dro.dur.ac.uk` and served by `www.mdpi.com` published one row:

```text
| www.mdpi.com | 1 | 1 | 1 | 100% |
```

No row named Durham at all. The 403 that really happened vanished under a column header that reads "Links tried". The column that exists to say which hosts refuse became the column that hid a refusal.

**Root cause:** before ADR 0012, one Paper meant at most one link, so a count of Papers really was a count of links. The rule changed from one to one into one to many, and the aggregate still keyed on the one. The new `attempts` counter in the command output shows that the author already knew a Paper now costs several requests.

**Fix:** `OpenCopyResult` carries `tried_hosts`, a tuple of hosts in the order Fynd asked them, and `attempts` is the length of that tuple. `host_rows` adds one link for every host in the tuple, and it adds the file and the usable text to the host that answered. One column counts requests and the other counts answers, and the two no longer share a key.

**Verification:** a test gives one Paper two hosts and one file. It asserts two rows, which are Durham with one link and no file, and MDPI with one link, one file and one usable text. The suite passed at 151 tests with ruff clean.

**Prevention:**

- A change from one to many breaks every aggregate that keyed on the one. Search for the field name, list every reader, and ask each reader what it counts.
- A column header is a claim. Read the header out loud against the code that fills it.

---

## A slow host lost the other free copies of the same Paper

**Found:** 2026-10-11, by the same code review.

**What happened:**

`Fetcher.fetch` answers with `Fetched` or `Refused`, and it raises `FetchFailed` for a timeout or a second rate limit. The new loop over three candidates caught neither case, because it only read the returned answer. The error left `read_open_copy`, and `run_measure_open_copies` counted the Paper as dropped.

So a slow first candidate ended the Paper. A free `cc-by` PDF waiting as the second candidate was never asked for. The table said the run broke rather than naming a file it reached. The docstring of the loop said that a refused host never stops the run. That held for a 403 and silently did not hold for a timeout.

**Root cause:** the pipeline has two ways to say "no file", which are a returned refusal and a raised failure. The loop handled the one that arrives as a value and forgot the one that arrives as an exception.

**Fix:** each candidate runs inside a `try`, catches `FetchFailed`, remembers it, and moves on. After the loop, a Paper with no returned answer at all re-raises that error. The command still counts it as dropped, and nothing is cached. A refusal is an answer, so it wins over a failure as the stored reason.

**Verification:** three tests hold it. One times out on the first candidate and takes the file from the second. One times out on both and asserts the error still leaves the pipeline. One mixes a timeout and a 403 and asserts the 403 is the reason, with two attempts counted.

**Prevention:**

- Keep the two outcomes apart in the type and name them. `Fetched | Refused` is an answer, and an exception is the absence of one. Then decide, for each loop, which of the two ends it.
- Read what a call raises before you write the loop around it. A search for the raise sites of `FetchFailed` names both cases in ten seconds.

---

## A file that extracts to nonsense ended the Paper

**Found:** 2026-10-11, by the same code review, as a decision to take rather than a crash to fix.

**What happened:**

The loop returned as soon as one candidate downloaded, whatever the usable text rules said about its text. The docstring gave the reason, which is that a second candidate of one Paper is the same article.

That reason is true of the article and false of the file. The rules test the file. A scanned repository PDF extracts to glyph soup and fails `text_not_textual`, or a cover page fails `no_section_word`. The publisher copy of the same article is a born digital `cc-by` PDF that extracts cleanly. The ranking and the cap of three attempts were switched off in the one case where a second link pays most.

**Root cause:** the loop ended on progress and not on its goal. "A file arrived" is a step, and "the text is usable" is the answer the pipeline exists to produce.

**Fix:** the loop returns early only for Usable text. A file that fails a rule is held as `failed_file` and the loop goes on. With no better candidate, that held file is the answer. It beats a refusal that arrived after it, because the pipeline reached one step further with the file.

**Verification:** three tests hold it. One fails the first file and takes the second. One fails both and keeps the reason of the last file with both hosts recorded. One mixes a failed file and a later 403 and asserts the file reason wins. The measured cost is zero today, because 0 of 20 Papers failed a text rule on 2026-10-09.

**Prevention:**

- Name the success condition of a loop once, and break on that condition and not on a step toward it.
- Ask what a rule tests. A rule about a file is not an answer about the article, and three candidates are three files of one article.

---

## The blocklist missed the same host under another spelling

**Found:** 2026-10-11, by the same code review.

**What happened:**

`NO_FILE_HOSTS` holds `doi.org`, `dx.doi.org` and `doaj.org`, which are the hosts that hold no file. `holds_no_file` tested membership of that tuple with the exact `netloc`, and `host_of` neither lowercases nor drops a `www.` prefix. So `https://www.doaj.org/article/x` reads as `www.doaj.org` and passes the blocklist, and `https://DOI.org/...` passes it too. doaj.org is on the list because it refused two fetches with a 403 on 2026-10-09, and only its bare spelling was blocked.

**Root cause:** the one test for that function used the bare spelling, which is the spelling the measurement happened to produce.

**Fix:** `holds_no_file` lowercases the host and drops a leading `www.` before the membership test. One function owns that form, and the candidate ranking and the fallback link both call it.

**Verification:** one test asserts four spellings, which are `doaj.org`, `www.doaj.org`, `DOI.org` and a real repository host that stays allowed.

**Prevention:**

- Normalize before you compare. Any match against a list is a canonical form problem. The forms to think about are case, a `www.` prefix, a trailing dot and a port.
- A test that uses only the value your data produced today tests your data and not your rule.

---

## An open copy with no address read as a closed Paper

**Found:** 2026-10-11, by the same code review.

**What happened:**

`open_locations` deduplicated the locations of a work by their address. It dropped any location with neither a PDF link nor a landing page. OpenAlex sometimes marks a location as open and names no address at all. Take a work whose only open location is that one. `reason_for_no_candidate` then answered `no_open_location`, and the reason table reads that name as "this Paper is closed".

That is a different and stronger claim than the truth, which is that the Paper is open and Fynd holds no address to try. The comment two lines above stated the right intent and the code dropped the case.

**Root cause:** the function enumerated the cases the measured pool contained, which are open with a file and open with a landing page. It did not enumerate the cases the input allows.

**Fix:** such a location keeps its place in the count, marked by its position, so it still counts as open while it carries no address. `reason_for_no_candidate` then answers `no_pdf_link`, and `no_open_location` stays for a work OpenAlex marks open nowhere.

**Verification:** one test builds a work whose single open location holds no address, and asserts no candidate and the reason `no_pdf_link`.

**Prevention:**

- In a measurement, each name is a claim, so enumerate the cases of the input and not the cases you expect. Here they are four, which are open with a file, open with a landing page, open with no address, and not open.
- A table with two names for four cases hides the step that failed, which is the one thing the table exists to show.

---

## A Paper can vanish from the reason table

**Found:** 2026-10-11, by the same code review.

**What happened:**

`Resolution.reason` carries a default of the empty string, and `candidates_for` passed that value through to the result. The old shape had no default, so the author had to state a reason. A result with an empty reason is counted under no name in `reason_counts`, and `report` prints only the names in `reasons.ALL`. So that Paper leaves the table, and the table stops adding up to the size of the pool.

No path reaches it today, because the real resolver always names a reason. The type no longer prevents it.

**Root cause:** a closed set of strings gained a member that is not in the set, which is the empty string, through a field default.

**Fix:** `candidates_for` returns `answer.reason or reasons.NO_OPEN_LOCATION`, so every result carries a member of `reasons.ALL`.

**Verification:** one test builds a resolution that names no reason and asserts the result reason is in `reasons.ALL`. The reason table test asserts the count holds one key for every name in `reasons.ALL`.

**Prevention:**

- A closed set of strings lives in one module, and every producer returns a member of it. A field that defaults to the empty string is the hole.
- A published number needs an invariant, and this one is that the table sums to the pool. Write the invariant as a test and not as a sentence.

---

## One cache file in git can never be read

**Found:** 2026-10-11, by the same code review.

**What happened:**

A cache file was committed that holds `"shape": 2`, while `REPLY_SHAPE_VERSION` in `src/fynd/openalex.py` is 1. The file name is a hash of `{api, doi, shape}`, so no run computes that name again. The other 20 records hold shape 1.

Two costs followed. The repository carries dead bytes. The one Paper in the pool with no replayable record sends a live request on the next measurement. That breaks the sentence three lines above the constant, where the code says the 20 records replay with no lookup.

**Root cause:** a live run wrote the file while the constant was 2. The constant went back to 1, and `git add -A` then took the whole directory.

**Fix:** the file is deleted.

**Verification:** a replay of the committed records through the new rules gives 10 Papers with a candidate. The other 10 are 6 with no open location, 3 with a landing page only, and 1 whose every address holds no file. Those are the predicted numbers, so no other record is dead.

**Prevention:**

- Read `git status` and the diff of a commit that follows a live run, because a run writes files you did not write.
- A cache keyed by a hash of its input cleans itself. A cache keyed by a version number leaves an orphan every time that number moves.

---

## A near miss: the cache version that nearly deleted the replay

**Found:** 2026-10-11, by me, while running `resolve-open-copy` against a cached identifier and watching it say "OpenAlex holds no record".

**What happened:**

The candidate rules changed, so the version number in the OpenAlex cache key went from 1 to 2. That number is part of every key, so the 20 records in git became unreachable in one edit. The next measurement run sends 20 live requests, and the promise that a reader replays the measurement with no network is broken.

**Root cause:** the number names the shape of the stored value, and the edit treated it as a version of the parsing rules. The stored value is the raw OpenAlex reply plus a found flag, and `resolve` applies the candidate rules at read time. So new rules change no stored byte.

**Fix:** the number went back to 1, before the commit, and the comment beside it now says what the number belongs to.

**Verification:** the replay over the 20 committed records sends no request and gives 10 Papers with a candidate. That is the number the new rule predicted.

**Prevention:**

- Version the stored format and not the code that reads it. The question to ask is whether new code reading an old file produces a correct answer. A yes keeps the key, and a no earns the bump and the refetch that follows it.
- A cache key is a contract with every file already written under it. Count the files before you change the key.

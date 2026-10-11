# Bugs

One entry for each bug found in the code, newest day first. Each entry says what was wrong, what fixed it with the logic behind the fix, and what stops it from coming back.

A bug found by a code review before anyone ran the code is still a bug. It is here so the same mistake does not arrive twice.

## 2026-10-11, day 5

Twelve bugs, all of them fixed. Two of them stop a live measurement run, and one publishes a wrong number. The day added three things at once: a Paper tries up to three links, every link passes robots.txt, and a journal file counts as free. Most of the twelve come from the first of the three.

### 1. The host table hid the refusals it exists to show

A Paper now tries up to three links. The host table counted one link for each Paper and named only the host that answered last. A Paper refused at Durham and served by MDPI printed one row for MDPI. The Durham refusal vanished under a column header that reads "Links tried".

The fix. `OpenCopyResult` carries `tried_hosts`, which is a tuple of hosts in the order Fynd asked them, and `attempts` is the length of that tuple. `host_rows` in `measure.py` adds one link for every host in the tuple. It adds the file and the usable text to `open_copy.host`, which is the host that answered. So one column counts requests and the other counts answers, and the two no longer share a key.

The prevention. The bug is a one to many change under an aggregate that still keyed on the one. Before you let a step repeat, search for the field name and list every reader of the shape it writes. Ask each reader what it counts. The test that holds it is one Paper with two hosts and one file.

### 2. A slow host lost the other copies of the same Paper

A timeout raises an error instead of returning an answer. The loop over the three candidates did not catch it. A slow first host then ended the Paper, and Fynd never asked the second host for the free file it held.

The fix. The loop wraps each `fetch(url)` in a `try`, catches `FetchFailed`, remembers it, and moves to the next candidate. After the loop, a Paper with no answer at all re-raises that error. The command then counts it as dropped, and the reason table stays honest. A refusal is an answer, and it wins over a failure as the stored reason.

The prevention. Keep the two outcomes apart in the type. `Fetched | Refused` is an answer, and an exception is the absence of one. Then decide, for each loop, which of the two ends it. Read what a call raises, with a search for its raise sites, before you write the loop around it.

### 3. A redirect loop on robots.txt ends the whole run

The robots.txt fetch caught a timeout and a transport error. A redirect chain that never ends raises a third kind, which is not either of those. It escaped the fetch, the pipeline and the command. One bad host then stops the measurement on that Paper and loses every Paper after it.

The fix. `httpx.TooManyRedirects` joined the `except` clause of `fetch_robots`, and it maps to "no answer, and nothing cached". That class sits under `RequestError` and not under `TransportError`, which is why a tuple of two names missed it. The file fetch already caught it by name, so the two paths agree now.

The prevention. Catch by the exception tree of the library and not by memory. A command that loops over a pool needs one guard for each item, so one bad item costs one item and not the run. A test that raises the real exception class is the cheap proof.

### 4. A rate limit was stored, and it blocked a host for ever

A host that answers a robots.txt request with 429 is asking Fynd to come back later. Fynd stored that answer. A stored 429 reads as "allow nothing", and nothing in the cache expires, so that host was refused for ever.

The fix. The storable test is now `400 <= status < 500 and status != RATE_LIMIT_STATUS`, which matches RFC 9309, where a 429 sits with the 5xx answers as unreachable. `cache.write_refusal` already refuses a 429 through its `UNCACHEABLE_STATUS` guard, and the robots path called `cache.write` and walked around that guard.

The prevention. A status that means "ask again later" is never cacheable, so that rule belongs inside the cache module and not in each caller. A second write path around a guard is the shape to watch for. Where a docstring and the code disagree, the missing thing is a test.

### 5. The robots rules never expired

Fynd read a robots.txt once and kept it. A repository that adds a rule next week never won over the file Fynd read today, and a comment in the code claimed the opposite.

The fix. The stored value carries `read_at`, and `robots_is_stale` compares it against `ROBOTS_MAX_AGE_SECONDS`, which is 24 hours, the limit RFC 9309 names. A stale entry is read again from the host and written back with a new time.

The prevention. Every cache entry needs an answer to one question, which is how long its answer stays true. An entry keyed by a hash of its own input is true for ever, because new input makes a new key. An entry keyed by an address, such as a host and its robots.txt, has a lifetime, so store the time beside the value.

### 6. The robots.txt body had no size cap

The file fetch caps a body at 20 megabytes. The robots.txt fetch read whatever arrived.

The fix. `fetch_robots` reads through `client.stream` and stops at `ROBOTS_MAX_BYTES`, which is 500 kibibytes, the size RFC 9309 asks a crawler to read. The bytes decode as UTF-8 with replacement, because a rules file with one bad byte is still a rules file.

The prevention. Every network read needs three limits, which are a size cap, a timeout and a redirect cap. A buffered `client.get` has no size cap at all, so a capped read is a stream plus a counter. When you add a second call to a module, copy the limits of the first call and not only its shape.

### 7. A link with no host shared one answer with every other such link

A link such as `dro.dur.ac.uk/a.pdf`, with no `https://` in front, has an empty host. Every such link shared one robots entry. The rules of one host then govern another, and the request crashed on the address `https:///robots.txt`.

The fix. `is_fetchable(url)` demands a scheme of http or https and a host that is not empty, and `Fetcher.fetch` refuses anything else before it looks up robots.txt. The robots cache key holds the scheme and the host, because RFC 9309 scopes a rules file to one scheme and one authority.

The prevention. Check a value once, at the boundary where it enters your own rules, and let everything after that point trust it. An empty key is a shared key, and a shared key merges two things in silence. The identity of a cache entry belongs in its key and never in the caller's head.

### 8. The blocklist missed the same host under another spelling

`doaj.org` holds no file, and it was on the blocklist. `www.doaj.org` and `DOI.org` are the same hosts in another spelling, and they were not.

The fix. `holds_no_file` lowercases the host and drops a leading `www.` before it tests membership of `NO_FILE_HOSTS`. One function owns that form, and the pipeline and the fallback link both call it.

The prevention. Normalize before you compare. Any match against a list is a canonical form problem. The forms to think about are case, a `www.` prefix, a trailing dot and a port. One function owns the form, and every caller goes through it.

### 9. An open copy with no link read as a closed Paper

OpenAlex sometimes names a location as free and gives no address for it. The reason table read that Paper as having no free copy anywhere, which is a different and stronger claim.

The fix. `open_locations` keeps such a location and marks it by its position, so it still counts as open while it carries no address to try. `reason_for_no_candidate` then answers `no_pdf_link`, and `no_open_location` stays for a work OpenAlex marks open nowhere.

The prevention. In a measurement, each name is a claim, so enumerate the cases of the input and not the cases you expect. Here they are four: open with a file, open with a landing page, open with no address, and not open. A table with two names for four cases hides the step that failed.

### 10. A Paper can vanish from the reason table

The reason came straight from the lookup, and that lookup can hand back an empty reason. A Paper with an empty reason is counted under no name, so the table stops adding up to the size of the pool.

The fix. `candidates_for` returns `answer.reason or reasons.NO_OPEN_LOCATION`, so a result always carries a member of `reasons.ALL`. `reason_counts` builds its keys from `reasons.ALL`, so a name outside that tuple is counted and never printed.

The prevention. A closed set of strings lives in one module, and every producer of one returns a member of the set. A field that defaults to the empty string is the hole, so give it no default or give it a real name. One test asserts that every reason a result carries is in `reasons.ALL`.

### 11. A bad file ended the Paper

Three candidates are three files of one article, and the text checks test the file. Fynd stopped at the first file that downloaded. A scan that extracts to nonsense then ended the Paper, and a clean copy sat unread at the second link.

The fix. The loop returns early only for Usable text. A file that fails a check is held as `failed_file` and the loop goes on. With no better candidate, that held file is the answer. It beats a refusal that arrived after it, because the pipeline reached one step further with it.

The prevention. Name the success condition of a loop once, and break on that condition and not on a step toward it. "A file arrived" is progress and "the text is usable" is the goal. The same question fits any retry, which is what the check tests, the thing or the attempt.

### 12. One cache file in git can never be read

A cache file was written while a version number was set to 2, and the number went back to 1. The file was committed, and no later run can ever find it.

The fix. The file is deleted. Its name is a hash of `{api, doi, shape}`, so with the shape at 1 no run computes that name again.

The prevention. Read `git status` and the diff of a commit that follows a live run, because a run writes files you did not write. A cache keyed by a hash of its input cleans itself. A cache keyed by a version number leaves an orphan every time that number moves.

### A near miss worth writing down

The cache key for the OpenAlex answers held a version number for the stored shape. Changing the candidate rules looked like a change to that shape, so the number went up to 2. That throws away the twenty records in git and sends twenty live requests. It also breaks the promise that the measurement replays with no network.

The stored value is the raw reply plus a found flag, and `resolve` applies the candidate rules at read time. So new rules change no stored byte, and the number stays at 1. It went back to 1 before the commit.

The prevention. Version the stored format and not the code that reads it. The question to ask is whether new code reading an old file produces a correct answer. A yes keeps the key, and a no earns the bump and the refetch that follows it.

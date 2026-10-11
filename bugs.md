# Bugs

One entry for each bug found in the code, newest day first. Each entry says what was wrong, what fixed it, and what stops it from coming back.

A bug found by a code review before anyone ran the code is still a bug. It is here so the same mistake does not arrive twice.

## 2026-10-11, day 5

Twelve bugs. All twelve are fixed. Two of them stop a live measurement run, and one publishes a wrong number.

### 1. The host table hid the refusals it exists to show

A Paper now tries up to three links. The host table counted one link for each Paper and named only the host that answered last. A Paper refused at Durham and served by MDPI printed one row for MDPI. The Durham refusal vanished under a column header that reads "Links tried".

The fix. The result names every host it tried, in order, and the file and the text belong to the host that answered.

The prevention. When one step starts repeating, read every counter and every table that assumed it happened once.

### 2. A slow host lost the other copies of the same Paper

A timeout raises an error instead of returning an answer. The loop over the three candidates did not catch it. A slow first host then ended the Paper, and Fynd never asked the second host for the free file it held.

The fix. Each candidate catches the timeout and moves on. When no candidate answered at all, the error is raised, because the command counts such a Paper as dropped.

The prevention. A library raises more kinds of error than the one you remember. Read what each call can raise before you write the loop around it.

### 3. A redirect loop on robots.txt ends the whole run

The robots.txt fetch caught a timeout and a transport error. A redirect chain that never ends raises a third kind, which is not either of those. It escaped the fetch, the pipeline and the command. One bad host then stops the measurement on that Paper and loses every Paper after it.

The fix. A redirect loop reads as unreachable, which is what RFC 9309 calls it.

The prevention. The same as bug 2. Also, a command that runs over a pool must survive one bad item.

### 4. A rate limit was stored, and it blocked a host for ever

A host that answers a robots.txt request with 429 is asking Fynd to come back later. Fynd stored that answer. A stored 429 reads as "allow nothing", and nothing in the cache expires, so that host was refused for ever.

The fix. A rate limit is never stored. The comment and the record already said so, and only the code disagreed.

The prevention. Never cache an answer that means "ask again later". Make the code say what the record says, and hold it with a test.

### 5. The robots rules never expired

Fynd read a robots.txt once and kept it. A repository that adds a rule next week never won over the file Fynd read today, and a comment in the code claimed the opposite.

The fix. A stored robots answer is read again after one day, which is the limit RFC 9309 names.

The prevention. A cache with no expiry is a decision. Write it down, or set the limit the standard names.

### 6. The robots.txt body had no size cap

The file fetch caps a body at 20 megabytes. The robots.txt fetch read whatever arrived.

The fix. The body is cut at 500 kibibytes, which is the size RFC 9309 asks a crawler to read.

The prevention. Every fetch needs the same limits. A second fetch path in one file is where a limit goes missing.

### 7. A link with no host shared one answer with every other such link

A link such as `dro.dur.ac.uk/a.pdf`, with no `https://` in front, has an empty host. Every such link shared one robots entry. The rules of one host then govern another, and the request crashed on the address `https:///robots.txt`.

The fix. A link with no host, or with a scheme that is not http or https, is refused and never fetched. The scheme is part of the robots key now, because RFC 9309 scopes the rules to one scheme and one host.

The prevention. Check a link at the point where it enters the fetcher. Everything after that point trusts it.

### 8. The blocklist missed the same host under another spelling

`doaj.org` holds no file, and it was on the blocklist. `www.doaj.org` and `DOI.org` are the same hosts in another spelling, and they were not.

The fix. The host is lowercased, and a leading `www.` is dropped, before the blocklist is read.

The prevention. Make a value plain before you match it against a list.

### 9. An open copy with no link read as a closed Paper

OpenAlex sometimes names a location as free and gives no address for it. The reason table read that Paper as having no free copy anywhere, which is a different and stronger claim.

The fix. Such a Paper reads as "open, but no file link", which is its own counted reason.

The prevention. A reason table is a measurement. Each name must say exactly one thing, and a missing case must not borrow another name.

### 10. A Paper can vanish from the reason table

The reason came straight from the lookup, and that lookup can hand back an empty reason. A Paper with an empty reason is counted under no name, so the table stops adding up to the size of the pool.

The fix. An empty reason falls back to a real name.

The prevention. A published table must sum to its pool. Give every row a name it can be counted under.

### 11. A bad file ended the Paper

Three candidates are three files of one article, and the text checks test the file. Fynd stopped at the first file that downloaded. A scan that extracts to nonsense then ended the Paper, and a clean copy sat unread at the second link.

The fix. Usable text ends the attempts, and a file alone does not.

The prevention. Ask what a check tests. A check on a file is not an answer about the article.

### 12. One cache file in git can never be read

A cache file was written while a version number was set to 2, and the number went back to 1. The file was committed, and no later run can ever find it.

The fix. The file is deleted.

The prevention. Read what a run wrote before you commit it. A cache file keyed by a version is dead the moment that version changes.

### A near miss worth writing down

The cache key for the OpenAlex answers held a version number for the stored shape. Changing the candidate rules looked like a change to that shape, so the number went up to 2. That throws away the twenty records in git and sends twenty live requests. It also breaks the promise that the measurement replays with no network.

The stored value is the raw reply, and the rules read it at every call, so the shape never changed. The number went back to 1 before the commit.

The prevention. A cache version belongs to the stored bytes. Change it for a change in those bytes, and never for a change in the code that reads them.

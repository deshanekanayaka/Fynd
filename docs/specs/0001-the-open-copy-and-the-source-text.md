# Spec 0001: the Open copy and the Source text

Status: ready to build. Date: 2026-10-08.
This spec covers step 3 of the build sequence in [NEXT-STEPS.md](../../NEXT-STEPS.md).
It follows [ADR 0007](../adr/0007-the-open-copy-is-resolved-then-measured.md) and [ADR 0005](../adr/0005-a-claim-is-a-located-span.md). The words are the ones in [CONTEXT.md](../../CONTEXT.md).

## Problem Statement

A student reaches stage 3 and gets 3 candidate Problems, each with 2 Claims. A Claim is a sentence that exists in the Source text. Two character offsets prove it. Fynd holds no Source text today. The search returns a title, an abstract, and a link. Nothing fetches the file behind that link, and nothing turns it into text.

The link is also weaker than it looks. For the Seeded Topic, 12 of 20 Papers carry an Open copy link. 6 of those 12 point at doi.org, which is a redirect to a publisher page and not a file. So at most 4 of 20 Papers reach a file without more work.

Deshan has a second problem. The PRD promises a measured number for Source text extraction. That number is the share of Papers that give usable text, for each host. No code produces that number.

## Solution

Fynd resolves the Open copy a second time, fetches it, and turns it into one flat string with an offset map. One command then publishes the per host success rate.

For one Paper the work runs in this order.

1. OpenAlex is asked about the digital object identifier of the Paper.
2. A Paper that OpenAlex marks as retracted is dropped, and the drop is counted.
3. The repository Open copy and its license are read from the answer. Fynd ignores a publisher location.
4. The file is fetched under the fetch rules, and the raw bytes are cached.
5. The bytes are extracted into a Source text with an offset map. A PDF goes to pdfplumber, and an HTML page goes to trafilatura.
6. Three checks decide whether the Source text is usable.

A Statistic and a Product arrive as a web page, so the HTML half of the same work serves stage 3.

## User Stories

1. As a student, I want every Claim to come from text Fynd read, so that my supervisor finds the sentence in the paper.
2. As a student, I want a Paper whose publisher blocks downloads to drop out quietly, so that my Topic does not stall.
3. As a student, I want a retracted paper to never reach my handover, so that I do not defend a withdrawn finding.
4. As a student, I want the Statistic quoted from the page it lives on, so that the number is checkable.
5. As a student, I want to hear early that a Topic gives too little text, so that I pick again in time.
6. As Deshan, I want the raw bytes of every fetch on disk, so that a second extraction costs no download.
7. As Deshan, I want each Source text stored with its own content hash, so that an offset is true against one version.
8. As Deshan, I want the extractor name and version stored beside the text, so that a changed hash has a named cause.
9. As Deshan, I want one command that prints the per host success rate, so that the PRD promise carries a number.
10. As Deshan, I want the count of Papers dropped for a retraction, so that the guard shows up beside the Claim rejections.
11. As Deshan, I want every fetch and every OpenAlex answer cached, so that the whole step replays with no network.
12. As Deshan, I want a failed fetch to stay out of the cache, so that the next run tries again.
13. As Deshan, I want the fetch to refuse a body that is not a PDF, so that a login page stays out.
14. As Deshan, I want one request per second for each host, so that a repository administrator has no reason to block Fynd.
15. As Deshan, I want the user agent to name Fynd and the repository, so that an administrator can find the operator.
16. As Deshan, I want no code in this repository that scrapes a publisher, so that the project is defensible in a room.
17. As Deshan, I want the usable text rule written as three named checks, so that I can explain the number in an interview.
18. As Deshan, I want the extraction to return an offset map, so that stage 5 carries an offset back to the file.
19. As Deshan, I want the HTML path to exist now, so that stage 3 can quote a Statistic and a Product.
20. As Deshan, I want every test to run with no network and no key, so that continuous integration stays free.
21. As Deshan, I want the license from OpenAlex stored with the Source, so that the licensing risk has a per Source answer.
22. As a reviewer, I want one command to give me the table Deshan published, so that the number is evidence.

## Implementation Decisions

Four modules carry the work, and none of them knows about HTTP routes, the command line, or Postgres.

- An OpenAlex client. It takes a digital object identifier and returns the retraction flag, the repository Open copy link, and the license. It caches every answer, and it needs no key.
- A fetcher. It takes a link and returns the raw bytes with the host and the status it saw. It follows at most 3 redirects. It accepts a body only when the content type says PDF, or when the first bytes are `%PDF`. It caps the body at 20 megabytes and the request at 30 seconds. It retries once, and it makes at most one request per second for each host. It sends a user agent that names Fynd, the repository, and the operator email address. It caches the raw bytes, and it caches no failure.
- An extractor. It takes bytes or an HTML string and returns a Source text, an offset map, and the extractor name with its version. pdfplumber reads a PDF, and trafilatura reads an HTML page. Both are permissively licensed, which matters because this repository is public.
- A quality detector. It takes a Source text and returns usable or not usable, with the reason. It runs three checks. A minimum character count. A minimum share of letters and ordinary punctuation. The presence of one section word such as method, results, or conclusion. Each threshold is a named constant, tuned on the 12 links of the Seeded Topic.

One pipeline function joins them. It takes a Paper, a resolve function, and a fetch function. It returns a Source text with its hash, its license, and its extractor, or a reason the Paper gave none. The two functions are plain arguments, exactly as a Stage receives its search and its model in ADR 0006.

The command that publishes the table runs that pipeline over the Papers of the Seeded Topic and writes `docs/measurements/open-copy-hosts.md`. The table holds one row for each host. Each row carries the number tried, the number fetched, the number that gave usable text, and the share.

The `source` table already carries the columns this work fills. The digital object identifier, the license, the published year, the Source text with its hash, and the extractor. No schema change is needed. The database itself does not exist yet, so this step writes to disk and not to Postgres.

The offset chain starts at the string the extractor produced. A PDF holds no reading order, so an offset into the bytes names no sentence. Normalization and chunking compose their maps on top of the Source text later.

## Testing Decisions

A good test here states a behaviour a student or a reviewer sees. It never states the shape of a private function.

The seams, which need Deshan's agreement before the code is written.

1. The pipeline function takes the resolve function and the fetch function as arguments. A test passes two small functions and drives the whole order with no network. This is the highest seam. It is the same shape the Stage files already use.
2. The extractor and the quality detector take bytes or a string and return a value. They need no seam of their own, because they reach nothing.

Prior art lives in the current tests. `tests/test_stage2.py` passes fake search and model functions into a Stage. `tests/test_semantic_scholar.py` answers HTTP from memory with an httpx mock transport. `tests/test_claude.py` replaces the client class with a stand in. The new tests follow those three patterns and add nothing new.

What gets tested.

- The pipeline drops a retracted Paper, and counts the drop.
- The pipeline ignores a publisher location and takes the repository one.
- The pipeline reports a reason when no Open copy exists, when the fetch fails, and when the text is not usable.
- The fetcher refuses an HTML login page served with a PDF name, and refuses a body over the cap.
- The fetcher caches the bytes, and caches no failure.
- The extractor returns the same text and the same hash for the same bytes.
- An offset taken from the Source text reads the same sentence in the extracted string.
- The quality detector fails a page of font junk, fails a cookie wall, and passes a real paper.
- The table command produces the same table twice from the cache.

Two small fixture files are committed for the extractor tests: one short PDF and one saved HTML page. No test reaches the network, and no test needs a key.

## Out of Scope

- Claim extraction and the tiered verifier. They are the next spec.
- Chunking, embeddings, and anything that needs pgvector.
- The runner, the database, and FastAPI.
- The web search step that finds a Statistic and a Product. This spec builds the HTML extractor that step needs, and not the search.
- Any fetch from a publisher.
- A second Topic. Metric 1 and metric 2 pass on the Seeded Topic first.

## Further Notes

The first run over the Seeded Topic is the measurement. If the share of Papers that give usable text is low, the stage 2 threshold of 3 comes back for review. ADR 0008 already flags that risk.

This spec lives in the repository and not in an issue tracker. No tracker and no triage label vocabulary is set up for this project.

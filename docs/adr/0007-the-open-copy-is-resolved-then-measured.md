---
status: accepted
date: 2026-10-08
---

# The open copy is resolved a second time, and no publisher is fetched

Fynd fetches an Open copy from a repository, and never from a publisher. OpenAlex resolves the Open copy a second time, keyed by the digital object identifier. The host list comes from a measurement and not from a guess.

## The fact that forced this

The first live search for the Seeded Topic returned 20 Papers. 12 carry an Open copy link, and 18 carry a digital object identifier. The 12 links split by host:

| Host | Links |
|---|---|
| doi.org | 6 |
| www.sciencedirect.com | 2 |
| dro.dur.ac.uk | 1 |
| www.research.ed.ac.uk | 1 |
| www.mdpi.com | 1 |
| pdpublishers.com | 1 |

A doi.org link is a redirect to a publisher page. It is an address with no file behind it. So at most 4 of the 12 links point at a file today. The stage 2 threshold is 3 Papers with an Open copy. The stage 4 guard needs 2 Papers with usable text. A pool of 4 files is too close to both numbers.

## The decisions

A Paper keeps its digital object identifier. The day 2 code dropped the arXiv identifier and kept no other, and the second lookup needs a key.

OpenAlex is the second lookup. For one digital object identifier it returns the Open copy locations and the license, and it needs no key. Fynd takes the repository location and ignores the publisher location.

Fynd never fetches a publisher. A doi.org link is a key for the OpenAlex lookup and never a fetch target.

The host list is a measurement. Fynd fetches all 12 links of the Seeded Topic once and records what each host returned. The per host success rate in the PRD becomes the list.

The pipeline holds two extractors. One reads PDF bytes, and one reads an HTML page. Both return a flat string and an offset map. The HTML path is not optional. A Statistic and a Product arrive as a web page, and stage 3 needs a Claim from one of the two.

Usable text has a definition, and three cheap checks carry it. A minimum character count. A minimum share of letters and ordinary punctuation. The presence of one section word, for example method, results, or conclusion. The thresholds are tuned on the 12 links of the Seeded Topic.

The cache stores the raw bytes of every fetch. The extracted text is a second cached value, derived from those bytes.

## The fetch rules

The fetcher follows at most 3 redirects. It accepts the body only when the content type says PDF, or when the first bytes are `%PDF`. That second check catches a login page that arrives with a PDF name.

The body is capped at 20 megabytes and the request at 30 seconds. A failure gets one retry, then stops with a sentence that names the host. The fetcher makes at most one request per second per host.

The user agent names Fynd, the repository, and the operator email address. A repository administrator must be able to find the operator.

## The extractors

pdfplumber reads a PDF. It is MIT licensed, and pdfminer.six under it reads a two column paper, which is the normal shape of an energy paper.

trafilatura reads an HTML page. It removes the navigation, the cookie banner, and the footer, and returns the article text. If the measurement shows that it loses the tables on a statistics page, readability-lxml is the fallback.

The offset chain starts at the string the extractor produced. That string is the Source text. Offsets cannot point into the PDF bytes, because a PDF holds no reading order. Normalization and chunking compose their maps on top of the Source text. See [ADR 0005](./0005-a-claim-is-a-located-span.md).

The `source` table gains three columns. The digital object identifier, which is the lookup key. The license string that OpenAlex returned. The extractor name with its version, for example `pdfplumber 0.11.4`.

Fynd stores the Source text for any Open copy, and shows only the located quote with its citation. It never republishes the stored text. The PRD states that rule for an abstract, and one rule for both is easier to defend than two.

## The command and the table

One command produces the per host numbers: `uv run python -m fynd.cli measure-open-copies`. It writes `docs/measurements/open-copy-hosts.md`.

That directory holds every published number. The verifier table, the retrieval table, and the independence table join it, so a reviewer finds them in one place.

## Consequences

Every number in the per host table is reproducible, because the bytes stay on disk. A reader runs the command and gets the same table.

A different extraction library runs over the stored bytes with no new download. This matters because an offset and a text hash belong to one exact extraction. See [ADR 0005](./0005-a-claim-is-a-located-span.md).

The repository holds no code that scrapes a publisher. The cost is the Paper that is open at the publisher and nowhere else. The per host table counts those Papers, so the cost is visible and not hidden.

Fynd now calls three external services: Semantic Scholar, OpenAlex, and one web search step. Each call is cached on disk from the first run. See [ADR 0004](./0004-replayable-runs-and-versioned-prompts.md).

The share of Papers that reach usable text is now two multiplications and not one. The search finds the Paper, the second lookup finds a file, and the extractor produces text that passes the three checks. If that share is low for the Seeded Topic, the stage 2 threshold of 3 comes back for review.

Two words enter `CONTEXT.md`. Open copy names the free file. Source text names the one exact string a Claim points into.

## Considered options

Unpaywall as the second lookup. Rejected because it answers this one question and nothing else. OpenAlex answers the same question, and it carries the authorships and the three identifier kinds that day 10 needs for independence and identifier deduplication.

The Semantic Scholar link alone. Rejected because 6 of the 12 links are a doi.org redirect, which leaves 4 files for a Topic that needs 3.

A fetch of the publisher page behind the digital object identifier. Rejected because Elsevier blocks automated download, and a refusal page or a cookie page reads as text to a naive extractor. A Claim located in a cookie notice passes the citation guard and destroys the one promise Fynd makes.

An allowlist of hosts, written today from the four host names in the cached run. Rejected because the PRD already promises the per host success rate as a measured component. A guessed list is the opinion that number replaces.

A PDF extractor alone. Rejected because stage 3 needs a Claim from a Statistic or a Product, both of which arrive as a web page.

PyMuPDF for the PDF path. Rejected because it is AGPL licensed, and this repository is public. It reads layout better and runs faster, which is the cost of the choice.

pypdf for the PDF path. Rejected because it is the weakest of the three on a two column paper.

Hand written rules over BeautifulSoup for the HTML path. Rejected because the rules are a maintenance job for each host, and the measured table does not pay for one.

Offsets measured against the PDF bytes. Rejected because a PDF holds no reading order, so a byte position names no sentence.

No record of the extractor. Rejected because the text hash then says that the text changed, and nothing says what changed it.

A cache of the extracted text alone. Rejected because a change of extraction library then costs a new download of every Paper. The old numbers also lose the bytes they were measured on.

# Fynd

[![CI](https://github.com/deshanekanayaka/Fynd/actions/workflows/ci.yml/badge.svg)](https://github.com/deshanekanayaka/Fynd/actions/workflows/ci.yml)

Final year students pick a project by asking "what app can I build?". They build a
booking system, and the supervisor sends it back for weeks, because nobody showed
that the problem is real. Fynd turns the question around. You pick a subject, and Fynd
searches published research for sentences that state a real problem. It keeps a
sentence only when it can find that sentence word for word in the paper it came
from. You get up to three candidate problems, each one with the quotes and the
links behind it.

A chat assistant answers the same question in one second and cites nothing. That is
the difference this repository exists to measure.

Status: in progress, and far from finished. This README says what runs today and
what does not. [ROADMAP.md](./ROADMAP.md) holds the build order and the progress.

## What runs today

The paper pipeline runs end to end on the command line. Fynd searches Semantic
Scholar and finds the free copy of a paper through OpenAlex. It downloads that file
while obeying `robots.txt`, then turns the PDF or the web page into plain text. Every reply from
every website is cached on disk, so a second run costs nothing and returns the same
answer.

```
uv run python -m fynd.cli stage1                 # start a project in one subject area
uv run python -m fynd.cli stage2                 # propose subjects, count papers with a free copy
uv run python -m fynd.cli resolve-open-copy      # find the free file of one paper
uv run python -m fynd.cli fetch-open-copy        # download that file
uv run python -m fynd.cli extract                # turn the file into text
uv run python -m fynd.cli measure-open-copies    # print the per-website success table
uv run python -m fynd.cli measure-retrieval      # print the ranking table below
```

Not built yet: the sentence extractor and the word-for-word guard, so the grounding
number does not exist. Also no grouping into candidate problems, no agent, no web
interface, no database, and no deployment.

## The one measured finding

The question was which ranking method puts the relevant papers at the top. The
answer is that the method hardly mattered and the wording of the search mattered a
lot. Measured on 2026-10-20 over a pool of 60 papers, 39 of which were graded
relevant by hand.

| Ranking method | Relevant papers found in the top 20 |
|---|---|
| Keyword ranking (BM25), short search words | 51% (20 of 39) |
| Meaning ranking (Voyage embeddings, 1024 values) | 46% (18 of 39) |
| The four searches as the websites returned them | 44% (17 of 39) |

Two papers separate the best method from the middle one, which is noise on a pool
this size. Across the four wordings of the same search, the result moved from 10% to
36%. So Fynd spends its effort on the words it searches with, and uses the free
keyword ranking. The full table, with every row and every limit, is in
[docs/measurements/retrieval-table-2026-10-20.md](./docs/measurements/retrieval-table-2026-10-20.md).

## Stack

Python 3.12 with uv for packages. Anthropic Claude for the language model calls,
with every prompt stored as a file so a published number names the exact prompt
behind it. httpx for requests, pdfplumber for PDF text, trafilatura for web page
text, Pydantic for the data shapes. pytest and ruff run on every pull request. The
web interface, the database and the hosting are designed and not yet built.

## Run it

You need [uv](https://docs.astral.sh/uv/) and a `.env` file with
`SEMANTIC_SCHOLAR_API_KEY`, `ANTHROPIC_API_KEY` and `FYND_CONTACT_EMAIL`. The
contact address goes in the request header, because the paper hosts ask who is
downloading.

```
uv sync --extra dev
uv run pytest
uv run python -m fynd.cli stage1
```

The 290 tests need no network and no keys, so they run on a clean machine.

## Limits

One person built this and one person graded every published number, so no
agreement score between two graders exists. The quotes Fynd keeps are traceable to
their paper, which is not the same as true. Recall over a pool is recall inside that
pool, so a relevant paper that no search returned is invisible to every number here.

## The documents

[ROADMAP.md](./ROADMAP.md) is the order of the work and the current state.
[PRD.md](./PRD.md) is the scope and the success measures. [CONTEXT.md](./CONTEXT.md)
defines every domain word. [docs/adr/](./docs/adr/) records each decision and the
reason behind it.

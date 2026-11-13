# Fynd

Final year students often end up building a CRUD application, because they ask
"what can I build?" instead of "which problem should I solve?".

Fynd turns the question around. You pick a subject, and Fynd searches published
research for sentences that state a real problem. It keeps a sentence only when it
can find that sentence word for word in the paper it came from. You get up to three
candidate problems, each one with the quotes and the links behind it.

Status: in progress. The paper pipeline runs on the command line. The sentence
extractor, the web interface and the hosting are not built yet.
[ROADMAP.md](./ROADMAP.md) holds the build order and the current state.

## Stack

| Part | Technology |
|---|---|
| Language and packages | Python 3.12, uv |
| Language model | Anthropic Claude, with every prompt stored as a file |
| Paper search and metadata | Semantic Scholar API, OpenAlex |
| Embeddings | Voyage AI `voyage-3.5-lite` |
| Requests | httpx |
| Text out of files | pdfplumber for PDF, trafilatura for HTML |
| Data shapes | Pydantic |
| Tests and lint | pytest, ruff |
| Continuous integration | GitHub Actions |

Designed and not yet built: FastAPI, Postgres with pgvector on Supabase, Next.js
with shadcn/ui, Docker, Langfuse.

## Run it

Prerequisites: [uv](https://docs.astral.sh/uv/), Python 3.12, and a `.env` file in
the repository root with three values.

```
SEMANTIC_SCHOLAR_API_KEY=
ANTHROPIC_API_KEY=
FYND_CONTACT_EMAIL=
```

The contact address goes in the request header, because the paper hosts ask who is
downloading.

Install the dependencies and run the tests. The 290 tests need no network and no
keys.

```
uv sync --extra dev
uv run pytest
```

Run a command.

```
uv run python -m fynd.cli stage1                 # start a project in one subject area
uv run python -m fynd.cli stage2                 # propose subjects, count papers with a free copy
uv run python -m fynd.cli resolve-open-copy      # find the free file of one paper
uv run python -m fynd.cli fetch-open-copy        # download that file
uv run python -m fynd.cli extract                # turn the file into text
uv run python -m fynd.cli measure-open-copies    # print the per-website success table
uv run python -m fynd.cli measure-retrieval      # print the ranking table
```

## Documentation

- [ROADMAP.md](./ROADMAP.md): the order of the work and the current state.
- [PRD.md](./PRD.md): the scope, the success measures and the non-goals.
- [CONTEXT.md](./CONTEXT.md): the definition of every domain word.
- [docs/adr/](./docs/adr/): each decision and the reason behind it.
- [docs/measurements/](./docs/measurements/): every published number, with its date
  and its limits.

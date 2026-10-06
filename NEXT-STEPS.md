# Next steps

Updated: 2026-10-05. Target ship date: 2026-10-26.
Read [PRD.md](./PRD.md) for the product and [CONTEXT.md](./CONTEXT.md) for the vocabulary.

## Where the work stands

The foundation is settled. No code exists yet. The design tree is closed, and the three week plan in the PRD holds the day by day sequence.

Settled and written down:

- The Problem comes from the real world, and Sources prove it. See [ADR 0001](./docs/adr/0001-real-world-problem-with-literature-as-evidence.md).
- The vocabulary is fixed in `CONTEXT.md`. Use those words in code, in tables, and on screen.
- Seven stages, each saved and resumable. Stage 3 is the centre of the product.
- Access is a signed Invite code, and a Project lives behind a secret link. No accounts.
- The stack and the free tiers are chosen. See the technical direction table in the PRD.
- The seeded Topic is United Kingdom household energy forecasting.

## Open items that need a decision from Deshan

1. Who grades the 5 Projects for metric 2, and when. One evening is enough.
2. Which typeface pair and which colour scale. The design skills in this session can propose a token set.
3. Whether the Render free web service or a different free container host serves the backend on the day. Confirm the free tier before day 12.

The Stages and the subjects behind each one are listed in [docs/stages-and-prerequisites.md](./docs/stages-and-prerequisites.md).
The tables for stage 1 to stage 3 are in [docs/database-design.md](./docs/database-design.md).
The backend and machine learning concepts are defined in [docs/backend-and-ml-concepts.md](./docs/backend-and-ml-concepts.md).

## Immediate next task

Build stage 1 to stage 3, backend first, with no frontend.

1. Done. The Python project runs with pytest, type hints, and ruff.
2. Done. `python -m fynd.cli` searches the Semantic Scholar Academic Graph API for one Topic, and every response is cached on disk. The run needs `SEMANTIC_SCHOLAR_API_KEY` in a `.env` file, because the endpoint without a key answers 429.
3. Fetch and extract text from the arXiv PDF for each open Paper.
4. Extract Claims with Claude Haiku 4.5, one call per chunk, and reject a Claim whose text does not appear in the Source.
5. Produce 3 candidate Problems with their early evidence, as a command line run.

Make sure that step 5 runs end to end from the command line before any FastAPI endpoint or any React component exists.

## Do not do yet

- No requirements documents and no ERD drafting. That is release 2.
- No second Topic until metric 1 and metric 2 pass on the first.
- No frontend before day 15, except the token layer if a day frees up early.

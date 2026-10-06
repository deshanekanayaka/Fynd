# Fynd: Evidence First Project Finder

Owner: Deshan. Date: 2026-10-05. Target ship date: 2026-10-26.
Vocabulary lives in [CONTEXT.md](./CONTEXT.md). Every capitalised term here is defined there.

## Problem

Final year project students start from the wrong question. They ask "what app can I build?" instead of "what problem is real, and what do people already do about it?". The first question produces CRUD applications and management systems. These pass, but they carry no evidence and no technical depth, so supervisors reject them for weeks and the student loses the build time.

Students who do well start from a real Problem, prove it with Sources, show the Existing approaches, and only then design software. Almost no student knows this order exists. General chat assistants make it worse, because they return a finished app idea on request and cite nothing.

## Target user

A bachelor's student in week 1 to week 4 of project selection, with no research training and no supervisor approval yet. The project they must deliver is a full stack application with background research, requirements, a database design, and an API design. Fynd therefore proposes software one student can build in one academic year.

## Success metrics

Fynd succeeds if all four hold at ship date.

1. Grounding: on a hand-labelled set of 10 Sources, Fynd extracts 90 percent or more of the true Claims and invents none. This gate runs in continuous integration.
2. Quality: 4 of 5 complete Projects pass a human rubric with 3 questions. Is the Problem real. Is the Gap supported. Can a bachelor's student build the Technical core in one year.
3. Reliability: every stage returns in under 3 minutes, and a Project resumes correctly after the container restarts.
4. Accessibility: WCAG 2.2 AA is the target, axe-core passes in continuous integration, and one keyboard-only pass and one screen reader pass are written up.

Metric 1 and metric 2 are the filter for every later feature request. A feature that lowers either one does not ship.

## Scope for version 1

Seven stages, each one saved, each one resumable by a secret link.

1. The student picks a Domain from Technology, Healthcare, or Energy.
2. Fynd proposes 5 to 8 Topics. The student picks one.
3. Fynd states 3 candidate Problems with early evidence. The student picks one.
4. Fynd fetches Sources. The student builds the Shortlist.
5. Fynd deep reads the Shortlist and shows Claims, Existing approaches, and the Gap.
6. Fynd drafts the Proposal. The student accepts it or asks again.
7. Fynd exports the handover.

Stage 3 earns the product. Picking a Problem from three evidenced options is where the student learns the lesson. Stage 1 and stage 2 are dropdowns, and stage 7 is a file.

The evidence bar for a Gap is 3 or more Claims from independent Sources, with at least one Paper and at least one Statistic or Product.

Stage 2 and stage 3 have fixed rules. Stage 2 keeps the picked Topic only if the search returns 5 or more Papers with an open copy, and the student gets one re-roll of the Topic list. See [ADR 0002](./docs/adr/0002-topics-are-generated-then-verified.md). Stage 3 shows 2 Claims for each candidate Problem, and at least one of the 2 comes from a Statistic or a Product. A candidate Problem must name a place and a group of people as separate fields, and Fynd rejects one that leaves either field empty. The citation guard applies at stage 3 with no exception, so a candidate Problem whose Claims fail the check is dropped. The student gets one re-roll of the 3 candidate Problems, and a second rejection returns them to stage 2.

Every Proposal names a Technical core, and cites the Source it comes from. A Proposal without one does not ship to stage 7.

## The handover

The export is a conversation starter for the first supervisor meeting, not a specification. It holds the Problem with its evidence, the Existing approaches, the Gap, the Technical core, a rough feature list, a numbered reference list, and a short list of questions the student asks the supervisor.

## Non-goals for version 1

- No accounts, no passwords, no supervisor accounts. A signed Invite code grants access, and a secret link reaches a Project.
- No free text Topic entry. Fynd proposes Topics inside the 3 seeded Domains.
- No paywalled papers. Open abstracts and open full text only.
- No requirements documents and no ERD drafting. That is release 2.
- No revising a Project after export.
- No model fine-tuning and no model training of your own.
- No mobile app, no chat interface, no response streaming.
- No live integrations with official data sources beyond one search step.

## Technical direction

Each choice maps to a line that the job postings ask for. Engineering owns the library picks inside each row.

| Piece | Choice | Skill it proves |
|---|---|---|
| Backend | Python, FastAPI, pytest, type hints, ruff | Clean tested Python, APIs |
| Frontend | Next.js, TypeScript, shadcn/ui on a custom token layer | Frontend practice, semantic markup |
| Accessibility | WCAG 2.2 AA target, axe-core in continuous integration | A claim with a check behind it |
| Discovery | Semantic Scholar Academic Graph API with a key | Retrieval over a real corpus |
| Full text | Open copy fetch and text extraction, host still to decide | Data engineering on messy input |
| Real world evidence | One web search step for Statistics and Products | Context engineering |
| Storage | Supabase Postgres with pgvector | Vector databases, database design |
| Extraction | Claude Haiku 4.5, one call per chunk | Prompt engineering at volume |
| Drafting | Claude Opus 5, one call per Proposal | Quality where it is the product |
| Guard | A citation check that rejects a Claim with no source text | Guardrails |
| Evaluation | A frozen labelled set, a rubric, regression tests | Evaluation, the hardest line to fake |
| Tracing | Langfuse free tier, cost per Project | Observability |
| Serving | Docker, Render free web service, Vercel for the frontend | Prototype to production |

The job runs inside the FastAPI process as a background task, and the page polls for stage progress. No free tier runs a separate worker process. Stage state is written to the database after every stage, because the free container sleeps after 15 minutes of no requests and can restart mid-run. A scheduled ping keeps the Supabase project awake, because a free project pauses after one week of no activity.

Model cost is roughly 240,000 input tokens of extraction plus one drafting call. That is under one dollar per Project.

## Design direction

Structure comes from research tools, with Elicit as the reference for showing Claims with citations without drowning the reader. Colour and voice come from warm writing tools, and the empty states and the stage 3 copy carry that warmth, because the student is most uncertain there. Components are standard, so an input box feels like an input box. The theme is not the default: a chosen typeface pair, a chosen colour scale, a 5 step type scale, and one density. Stage 3 gets the one bespoke component, a problem picker that shows 3 Problems with their evidence side by side.

## Three week plan

- Days 1 to 3: Semantic Scholar fetch, full text, chunking, retrieval. A command line run returns cited Claims for one Topic. The first live search for the Seeded Topic returned no Paper with an arXiv identifier, so the full text source is an open decision in `NEXT-STEPS.md`.
- Days 4 to 6: Claim extraction, Existing approaches, Gap clustering against the evidence bar.
- Days 7 to 8: candidate Problems for stage 3, and Proposal drafting with the Technical core.
- Days 9 to 11: the labelled set, the rubric, the citation guard, regression tests, tracing.
- Days 12 to 14: FastAPI endpoints, background job, stage state, Docker, deployment.
- Days 15 to 18: frontend, token layer, the problem picker, accessibility passes.
- Days 19 to 20: buffer.
- Day 21: README, demo recording, metric numbers written down.

If a day slips, the evaluation harness still ships, and the third Domain is the first thing to cut.

## Risks

- PDF text extraction returns rubbish for some papers. The buffer on days 19 and 20 exists for this risk.
- The model invents a Claim that no Source states. The citation guard and metric 1 exist for this risk.
- Semantic Scholar allows 1 request per second on search with a key, so stage 4 is slow by design. Cache every fetch on disk from day 1.
- A Problem reads well but a bachelor's student cannot build the Technical core in one year. Metric 2 tests exactly this, and it is the failure that an academic sounding proposal hides.
- Publisher abstracts are not licensed for redistribution. Fynd shows a short quote with a citation, and never republishes a stored abstract in full.
- The seeded Topic is UK household energy forecasting. Pick a second Topic only after metric 1 and metric 2 pass on the first.

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

## Measured components

The four metrics above gate the ship date. This section is different. It names the parts of Fynd that carry a number of their own, and where that number is published. A part with no number is a prompt, and a reviewer cannot tell a good prompt from a lucky one.

| Component | Number it publishes | Where it lives |
|---|---|---|
| Claim extraction | Recall and invention rate on the labelled set of 10 Sources | Continuous integration, metric 1 |
| The citation guard | Precision and recall at each tier threshold, and the chosen operating point | A table in the repository |
| Retrieval | Recall at 20 and nDCG for four configurations, on a hand labelled set of 40 to 60 Papers | A table in the repository |
| The embedding choice | The same two numbers for two embedding models on the same set | The same table |
| Source text extraction | The share of Papers that give usable text, for each host | A table in the repository |
| Source independence | The share of pairs the identifier resolver gets right, on 50 hand labelled pairs | A table in the repository |
| Dropped evidence | The count of dropped Claims by reason and tier, and the count of retracted Papers | A file in the repository |
| Every Stage | Tokens, cost, and 95th percentile latency | Langfuse, and the README |

Every number above is produced by a command anyone runs from the repository, against data in the repository. That is the difference between a number and a claim.

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

Stage 2 and stage 3 have fixed rules. Stage 2 keeps the picked Topic only if the search returns 3 or more Papers inside the Evidence window with an Open copy, and the student gets one Re-roll of the Topic list. A Topic under the threshold costs the student nothing. The count shows next to that Topic, the rest of the list stays pickable, and the Re-roll stays for a list that holds nothing the student wants. Stage 4 carries one guard for the same reason. When fewer than 2 Papers of a kept Topic give usable text, Fynd says so at stage 4 and offers the Topic list again. See [ADR 0002](./docs/adr/0002-topics-are-generated-then-verified.md). Stage 3 gathers the evidence first and then groups it. Fynd collects Claims for the kept Topic, verifies each one, and groups the survivors into 3 candidate Problems. A Claim that proves the Problem is real must come from a Source inside the Evidence window of 5 years, and the year shows on every Claim. An Existing approach and the Technical core carry no window, because a 2018 method paper is good evidence and a good Technical core. Fynd drops a Paper that OpenAlex marks as retracted, and counts the drop. When the evidence supports fewer than 3 candidate Problems, Fynd shows fewer cards with one sentence that says why, and never invents a third. Stage 3 shows 2 Claims for each candidate Problem, and at least one of the 2 comes from a Statistic or a Product. A candidate Problem must name a place and a group of people as separate fields, and Fynd rejects one that leaves either field empty. The citation guard applies at stage 3 with no exception, so a candidate Problem whose Claims fail the check is dropped. The student gets one Re-roll of the 3 candidate Problems, and a second rejection returns them to stage 2.

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
| Retrieval | Hybrid search over Postgres `tsvector` and pgvector, scored against a hand labelled set | Retrieval evaluation, recall at k, nDCG |
| Open copy | OpenAlex resolves the Open copy by digital object identifier, and no publisher is fetched | Working with a real, broken supply of files |
| Source text | Open copy fetch, PDF and HTML extraction, and a quality detector with a per host success rate | Data engineering on messy input |
| Real world evidence | One web search step for Statistics and Products | Context engineering |
| Storage | Supabase Postgres with pgvector and `tsvector` | Vector databases, database design |
| Extraction | Claude Haiku 4.5, one call per chunk | Prompt engineering at volume |
| Drafting | Claude Opus 5, one call per Proposal | Quality where it is the product |
| Guard | A tiered verifier, from exact match to entailment, with thresholds tuned on the labelled set | Guardrails, faithfulness scoring |
| Provenance | Character offsets carried through extraction, normalization, and chunking | Verifiable citations |
| Independence | A coauthor graph rule, and identifier deduplication across three identifier kinds | Graph work, entity resolution |
| Replay | Prompts as versioned files, and a cache keyed by every value that changes the answer | Prompt versioning, repeatable evaluation |
| Evaluation | A frozen labelled set, a rubric, regression tests | Evaluation, the hardest line to fake |
| Tracing | Langfuse free tier, with tokens, cost, and 95th percentile latency for each Stage | Observability |
| Serving | Docker, Render free web service, Vercel for the frontend | Prototype to production |

The Stage runs inside the FastAPI process as a background task, and the page polls for Stage progress with a plain `GET` every 3 seconds. No free tier runs a separate worker process. Fynd uses neither WebSockets nor long polling. A Stage sends one event, which is done or failed, and the page needs the new data in a request anyway, so a socket buys lower latency on a Stage that takes up to 3 minutes. A socket and a held request also keep a worker busy for that whole time on a free tier that runs few workers, and a sleeping container drops the connection, which then needs reconnect code beside the code that already reads the saved state. See [ADR 0003](./docs/adr/0003-four-routes-with-short-polling.md). Stage state is written to the database after every stage, because the free container sleeps after 15 minutes of no requests and can restart mid-run. A scheduled ping keeps the Supabase project awake, because a free project pauses after one week of no activity.

Model cost is roughly 240,000 input tokens of extraction plus one drafting call. That is under one dollar per Project.

## Design direction

Structure comes from research tools, with Elicit as the reference for showing Claims with citations without drowning the reader. Colour and voice come from warm writing tools, and the empty states and the stage 3 copy carry that warmth, because the student is most uncertain there. Components are standard, so an input box feels like an input box. The theme is not the default: a chosen typeface pair, a chosen colour scale, a 5 step type scale, and one density. Stage 3 shows the 3 candidate Problems as three standard cards side by side, each with its 2 Claims and their citations. The bespoke problem picker was cut on 2026-10-07 to pay for the measured components, and the cards carry the same information in the same order.

## Three week plan

Revised on 2026-10-07. The first version of this plan put one number on one component. This version puts a number on six, and pays for it with the cuts below.

- Days 1 to 2: done. The Semantic Scholar search with the disk cache. The design closed for the HTTP interface, the stage 2 rules, and the fields a Paper keeps.
- Days 3 to 4: the replayable core. Prompts as files with a version. The cache keyed by the model, the prompt version, the input hash, the decoding parameters, and the schema version. Open copy fetch and Source text extraction, with the quality detector and the per host success rate. Chunking that carries an offset map, so a Claim offset leads back to the raw file.
- Days 5 to 6: the labelled set of 10 Sources, Claim extraction with Haiku 4.5, and the tiered verifier. Day 6 ends with the precision and recall table at each threshold and the chosen operating point.
- Day 7: the retrieval labelled set. 40 to 60 Papers on the Seeded Topic, labelled by hand as relevant or not relevant.
- Days 8 to 9: hybrid retrieval over `tsvector` and pgvector, two embedding models compared on that set, and the configuration table with recall at 20 and nDCG. This closes the embedding decision with a measurement instead of a preference.
- Day 10: independence as a coauthor graph rule, with identifier deduplication across the digital object identifier, arXiv, and Semantic Scholar identifiers.
- Days 11 to 12: Existing approaches, Gap clustering against the evidence bar, candidate Problems for stage 3 with the web search step for a Statistic and a Product, and Proposal drafting with the Technical core.
- Days 13 to 14: FastAPI with the four routes, the background Stage, `stage_run`, Docker, deployment, and tracing with tokens, cost, and latency for each Stage.
- Days 15 to 18: frontend, the token layer, three standard cards at stage 3, and the accessibility passes.
- Day 19: buffer.
- Days 20 to 21: metric 2 grading of 5 Projects, the README with every number in it, the architecture diagram, and the demo recording.

The new work costs about 7 days. Four and a half of those come from work it replaces rather than adds. The tiered verifier replaces the plain citation check in the old days 9 to 11. The retrieval table replaces the unmeasured retrieval step in the old days 1 to 3. Tracing was already in the plan. The rest comes from three cuts.

- Two Domains ship instead of three. Which two is an open decision in `NEXT-STEPS.md`.
- Stage 3 shows three standard cards instead of one bespoke problem picker.
- The buffer drops from two days to one.

If a day slips, cut in this order. The retrieval table shrinks from four configurations to two, which keeps the embedding comparison and drops the fusion row. The independence rule keeps the venue and year check and drops the coauthor graph. The handover export loses its questions list. The evaluation harness and the verifier table ship whatever happens, because without them Fynd is a wrapper around a model.

## Risks

- PDF text extraction returns rubbish for some papers. The buffer on days 19 and 20 exists for this risk.
- The model invents a Claim that no Source states. The citation guard and metric 1 exist for this risk.
- Semantic Scholar allows 1 request per second on search with a key, so stage 4 is slow by design. Cache every fetch on disk from day 1.
- A Problem reads well but a bachelor's student cannot build the Technical core in one year. Metric 2 tests exactly this, and it is the failure that an academic sounding proposal hides.
- Publisher abstracts are not licensed for redistribution. Fynd shows a short quote with a citation, and never republishes a stored abstract in full.
- The seeded Topic is UK household energy forecasting. Pick a second Topic only after metric 1 and metric 2 pass on the first.

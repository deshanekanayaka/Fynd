# Fynd: Evidence First Project Finder

Owner: Deshan. Original date: 2026-10-05. Original target ship date: 2026-10-26.
Design review closed: 2026-11-07. Baseline target date: TBD.
Vocabulary lives in [CONTEXT.md](./CONTEXT.md). Every capitalised term here is defined there.

## Problem

Final year project students start from the wrong question. They ask "what app can I build?" instead of "what problem is real, and what do people already do about it?". The first question produces CRUD applications and management systems. These pass, but they carry no evidence and no technical depth, so supervisors reject them for weeks and the student loses the build time.

Students who do well start from a real Problem, prove it with Sources, show the Existing approaches, and only then design software. Almost no student knows this order exists. General chat assistants make it worse, because they return a finished app idea on request and cite nothing.

## Target user

A bachelor's student in week 1 to week 4 of project selection, with no research training and no supervisor approval yet. The project they must deliver is a full stack application with background research, requirements, a database design, and an API design. Fynd therefore proposes software one student can build in one academic year.

## Success metrics

Fynd succeeds if all four hold at ship date.

1. Grounding: on a hand-labelled set of 10 Sources, Fynd extracts 90 percent or more of the true Claims and invents none. This gate runs in continuous integration. The 10 Sources carry an open license, because their text is committed and continuous integration replays it. See [ADR 0011](./docs/adr/0011-the-public-repository-holds-the-text-and-not-the-files.md).
2. Quality: 4 of 5 complete Projects pass a human rubric with 3 questions. Is the Problem real. Is the Gap supported. Can a bachelor's student build the Technical core in one year. The author grades, which the README states as a limit, and the 5 handovers ship in the repository so a reader regrades them.
3. Reliability: every stage returns in under 3 minutes, and a Project resumes correctly after the container restarts.
4. Accessibility: WCAG 2.2 AA is the target, axe-core passes in continuous integration, and one keyboard-only pass and one screen reader pass are written up.

Accessibility is version 1 work alongside frontend development, not an optional stretch after AWS or MCP. Automated coverage must include meaningful interface states such as Candidate Problem cards, the evidence panel, loading, thin evidence, and failures, rather than only the initial screen. Automated scans supplement the documented keyboard and screen-reader passes; they do not establish compliance by themselves.

Metric 1 and metric 2 are the filter for every later feature request. A feature that lowers either one does not ship.

Build order agreed on 2026-11-07: complete Stages 3 to 7 using the current fixed Stage 3 sequence before adding an agent or other optional technologies. The complete path includes the evidence checks, saved Stage state, and export. Measure metric 1 and review the 5 complete Projects for metric 2 before starting those additions. Visual polish can follow the first complete path; reliability and accessibility remain version 1 requirements. The purpose is to identify failures in the current design and give each later addition a measured comparison.

## Baseline completion

The baseline is complete and measured when all of these are available:

- A live link where a stranger with an Invite can go from Domain to Export.
- A README with the measured-components summary, retrieval table and initial verifier table near the top, followed by a short "Why not just use ChatGPT?" explanation. It describes Claims as Source-grounded and traceable, not established truth. The production guard does not use a commercial LLM judge; that judge is an offline experimental competitor only.
- A recorded example of a rejected Claim or fewer than 3 Candidate Problems.
- A grounding measurement and 5 complete Projects reviewed against the rubric, with results and failures disclosed.
- Baseline quarantine and a small Injection set check, restart and retry checks, accessibility checks and manual passes, Langfuse tracing, and CI checks for the implemented promises.

Completing a measurement is not the same as meeting its target. Report each metric as passed, failed, or not yet established. The measured baseline is the prerequisite for experiments; release readiness still requires the product gates above. Every experiment has a time box set before it starts. The baseline target date and time boxes remain TBD, not an extension of the expired original ship date.

## Measured components

The four metrics above gate the ship date. This section is different. It names the parts of Fynd that carry a number of their own, and where that number is published. A part with no number is a prompt, and a reviewer cannot tell a good prompt from a lucky one.

| Component | Number it publishes | Where it lives |
|---|---|---|
| Claim extraction | Recall and invention rate on the labelled set of 10 Sources | Continuous integration, metric 1 |
| The citation guard | Precision and recall at each tier threshold, and the chosen operating point | A table in the repository |
| Retrieval | Recall at 10 and 20, and nDCG at 10, for five configurations, on the Retrieval set of 40 to 60 Papers | A table in the repository |
| The vector size | The same numbers for one embedding model at 1024 and at 512, which sets the pgvector column | The same table |
| Source text extraction | The share of Papers that give usable text, for each host | A table in the repository |
| Source independence | The share of pairs the identifier resolver gets right, on 50 hand labelled pairs | A table in the repository |
| Dropped evidence | The count of dropped Claims by reason and tier, and the count of retracted Papers | A file in the repository |
| Prompt injection defence | Attack outcomes and legitimate Claim recovery on clean and attacked versions of the Injection set, with explicit denominators | A table in the repository |
| Claim-to-Problem support experiment | Feasibility pilot first; model precision, recall, F1, thresholds, latency, cost and peak memory only when an adequate independent evaluation exists | Dated experiment reports, not a baseline gate |
| Every Stage | Tokens, cost, and 95th percentile latency | Langfuse, and the README |

Every number above is produced by a command anyone runs from the repository, against data in the repository. That is the difference between a number and a claim.

## Scope for version 1

Seven stages, each one saved, each one resumable by a secret link.

1. The student picks a Domain from Technology or Energy.
2. Fynd proposes 5 to 8 Topics. The student picks one.
3. Fynd states 3 candidate Problems with early evidence. The student picks one.
4. Fynd fetches Sources. The student builds the Shortlist.
5. Fynd deep reads the Shortlist and shows Claims, Existing approaches, and the Gap.
6. Fynd drafts the Proposal. The student accepts it or asks again.
7. Fynd exports the handover.

Stage 3 earns the product. Picking a Problem from three evidenced options is where the student learns the lesson. Stage 1 and stage 2 are dropdowns, and stage 7 is a file.

The evidence bar for a Gap is 3 or more Claims from independent Sources, with at least one Paper and at least one Statistic or Product.

Stage 2 and stage 3 have fixed rules. Stage 2 keeps the picked Topic only if 3 or more Papers inside the Evidence window hold an Open copy Fynd may fetch, and the student gets one Re-roll of the Topic list. The search returns 50 Papers and the ranking cuts them to 20. The count asks OpenAlex about each Paper of that top 20, and counts the Papers that name a free file on a host that holds one. See [ADR 0013](./docs/adr/0013-retrieval-ranks-in-python-over-a-pool-cut-to-20.md). It never counts the open link Semantic Scholar reports, because that link is often a lookup address with no file behind it. A Topic under the threshold costs the student nothing. The count shows next to that Topic, the rest of the list stays pickable, and the Re-roll stays for a list that holds nothing the student wants. Stage 4 carries one guard for the same reason. When fewer than 2 Papers of a kept Topic give usable text, Fynd says so at stage 4 and offers the Topic list again. Stage 4 shows the 20 Papers with the keeps already ticked, caps the Shortlist at 10, and explains each card with facts and not with a written sentence. See [ADR 0014](./docs/adr/0014-stage-4-pre-selects-and-a-card-explains-with-facts.md). See [ADR 0002](./docs/adr/0002-topics-are-generated-then-verified.md). Stage 3 gathers the evidence first and then groups it. Fynd collects Claims for the kept Topic, verifies each one, and groups the survivors into 3 candidate Problems. A Claim that proves the Problem is real must come from a Source inside the Evidence window of 5 years, and the year shows on every Claim. An Existing approach and the Technical core carry no window, because a 2018 method paper is good evidence and a good Technical core. Fynd drops a Paper that OpenAlex marks as retracted, and counts the drop. When the evidence supports fewer than 3 candidate Problems, Fynd shows fewer cards with one sentence that says why, and never invents a third. Stage 3 shows 2 Claims for each candidate Problem, and at least one of the 2 comes from a Statistic or a Product. A candidate Problem must name a place and a group of people as separate fields, and Fynd rejects one that leaves either field empty. The citation guard applies at stage 3 with no exception, so a candidate Problem whose Claims fail the check is dropped. The student gets one Re-roll of the 3 candidate Problems, and a second rejection returns them to stage 2.

Every Proposal names a Technical core, and cites the Source it comes from. A Proposal without one does not ship to stage 7.

## The handover

The export is a conversation starter for the first supervisor meeting, not a specification. It holds the Problem with its evidence, the Existing approaches, the Gap, the Technical core, a rough feature list, a numbered reference list, and a short list of questions the student asks the supervisor.

## Non-goals for version 1

- No accounts, no passwords, no supervisor accounts. A signed Invite code grants access, and a secret link reaches a Project.
- No free text Topic entry. Fynd proposes Topics inside the 2 seeded Domains. A free text search bar is designed for release 2, and the design is in the day 8 entry of [NEXT-STEPS.md](./docs/history/next-steps-2026-10.md). The Domain list also grows in release 2, with 10 as the target.
- No paywalled papers. Open abstracts and open full text only.
- No requirements documents and no ERD drafting. That is release 2.
- No revising a Project after export.
- No model training or fine-tuning in the initial product. After baseline completion and measurement, a bounded Claim-to-Problem support experiment may include training a logistic regression baseline and a LoRA fine-tune. It has learning value even if neither trained model ships. A trained model enters the product only if it demonstrates a worthwhile improvement over simpler alternatives on an adequate independent Fynd evaluation, preserves the product gates, and fits the hosting constraints. The experiment's data, budgets, time box, and deployment criteria must be settled before implementation.
- No mobile app, no chat interface, no response streaming.
- No live integrations with official data sources beyond one search step.

The model comparison targets Claim-to-Problem support, separately from locating Claims. It is staged, not a requirement to complete a four-model study before shipping. Start with a small pilot of verified Claim/Candidate Problem pairs from the planned Claim set Sources and the reviewed Projects. An assistant may prepare pairs, but Deshan labels them before seeing predictions. The pilot tests whether the task is clear and manageable; it cannot establish model superiority or production accuracy.

Use candidate negatives from other Candidate Problems within the same Topic, checking each by hand because swapping a Claim does not guarantee a negative. Report easy cross-Topic negatives separately. Record whether a Claim supports a particular factual assertion rather than requiring every Claim to establish an entire multi-part Problem. The exact label contract and treatment of partial support must be settled before model work. Mark ambiguous or specialist examples uncertain, report exclusions, and revise the task if labels are often uncertain. Candidate counts, label balance, and statistical uncertainty must be measured, not assumed from 5 Projects.

If adequate evaluation data can be obtained, compare a simple classifier and an existing NLI model. LoRA and an LLM judge are bounded later experiments; stop when further work offers little value. SciFact labels can support training, but its scientific statements and abstract evidence differ from Fynd's real-world Claims and generated Problems. Transfer quality is unknown until measured. Training, prompt/threshold development, and final evaluation stay separate, including by Source and related Problem where reuse could leak information. No fixed uncertainty margin or close model ranking is claimed from the pilot. The LLM judge is a competitor checked against human labels, never the grading authority for the other models. It runs manually for dated measurements, outside continuous integration.

Run the support study offline after Stage 3 grouping. If adopted, a support check belongs after grouping and before cards reach the student. It judges the Claim's attachment, not whether the located Claim should exist at all. Extending it to the Gap is a later hypothesis requiring its own task definition and evaluation, not automatic adoption of the same check. Metric 2 remains the baseline check on grouping under ADR 0008.

The Injection set starts small and covers inputs Fynd actually reads, including Paper abstracts, fetched pages, and metadata passed to models. A small check of the quarantine boundary is baseline work; expand the set for later agent experiments. Each attack has an explicit forbidden outcome and a paired clean input. Reuse checked passages where possible. Report successful attacks, safe continuation, deliberate refusal, and technical failure separately, alongside legitimate Claim recovery. A crash or blanket refusal must not count as useful safe completion. Cached model-answer replay checks the handling of those answers; changed prompts or models require fresh measured runs to assess changed model behaviour. The initial examples, measurement command, and replay checks remain to be designed.

## Technical direction

### Source text boundary

Source text is untrusted data, including text inside a verified Claim. Extraction calls have no tools, and their prompts wrap and label Source text as data. Any future Stage 3 agent receives verified Claims, necessary metadata, and structured outcomes instead of Source text or Source passages. Verification runs inside each evidence tool before Claims are returned, so the agent cannot bypass it. Structured outcomes and counts explain failures without supplying Source passages.

The student can inspect a cited Claim with its Source passage and original link. That human-facing retrieval is unavailable to the agent, and opening it does not send the passage to the agent. This boundary reduces exposure to prompt injection; locating a Claim does not prove that its words are safe, true, or relevant. See the draft [ADR 0016](./docs/adr/0016-source-passages-stay-outside-the-agent.md). The precise frontend layout remains undecided.

### Committed Stage 3 experiment

After the baseline is complete and measured, build and measure a time-boxed bounded LangGraph agent. Building the experiment is committed; production adoption is conditional. ADR 0008 remains the initial production design, and other Stages retain code-defined control flow. Compare the fixed sequence, explicit recovery rules, and the agent on declared Topic cases and resource limits. Classify Stage 3 failures against Candidate Problem requirements, not the later Gap's separate evidence bar. An exploratory batch of about 10 Topics is a proposed starting scope, not an adequate held-out evaluation by itself.

The agent may select a permitted search, rewrite search words, and stop. Code enforces evidence rules and output acceptance. Eight tool calls is a starting proposal; define the unit and all resource caps before implementation. Reserve budget for grouping and checks. On budget exhaustion, show only supported Candidate Problems under the existing thin-evidence rules, without automatic budget increases. Publish tokens, cost and latency per agent action in addition to Stage tracing. Adopt the agent only if its improvement in Topics yielding supported Candidate Problems is meaningful relative to simpler rules and its cost. Publish the experiment even if adoption is rejected.

### Non-functional design values still to settle

The existing Seeded Topic gate still applies: additional Topics in the exploratory batch wait until metric 1 and metric 2 pass on the first. A completed but failing measurement is not permission to expand Topic scope or claim release readiness.

These named placeholders record unresolved design inputs. They are not configured limits or measured results.

| Placeholder | Status and decision needed |
|---|---|
| `BASELINE_TARGET_DATE` | TBD; the original ship date is expired. |
| `PROJECT_SPEND_LIMIT` | TBD; distinguish the spending ceiling from measured and cached replay costs. |
| `AGENT_TOOL_CALL_UNIT` | TBD; define whether one call can perform multiple fetches or model calls. |
| `AGENT_TOOL_CALL_CAP` | 8 is an experimental proposal, not a validated value. |
| `AGENT_TOKEN_CAP` | TBD; include reserved grouping/checking capacity and work inside tools. |
| `STAGE_EXECUTION_BUDGET` | Existing target: under 3 minutes; define timing boundaries and agent/tool sub-budgets. Report cold startup, execution and time to usable results separately. A quick acknowledgement does not satisfy completion latency. |
| `FUZZY_MATCH_THRESHOLD` | TBD from development data and separate evaluation; no fuzzy tier in the initial verifier. |
| `SUPPORT_DECISION_THRESHOLD` | TBD only after the support task, label rules and adequate evaluation are defined; the pilot is not a production gate. |
| `MODEL_MEMORY_LIMIT` | TBD from the chosen deployment's verified allowance; measure peak process memory, startup and inference before selecting or training a model. No model family is presumed to fit. |
| `EXPERIMENT_TIME_BOXES` | TBD individually before agent, fuzzy, support-model, AWS or MCP work starts. |

The local-model memory check is an early experiment prerequisite, not permission to extend baseline scope. Verify host limits, dependency size and runtime overhead rather than relying on an assumed 512 MB allowance or on model names. The runtime cache's durable storage and the distinction between active work and waiting for a student's Pick also need design. Local filesystem cache survival is not implied by saving Project rows in Supabase.

### Stack

Each choice maps to a line that the job postings ask for. Engineering owns the library picks inside each row.

| Piece | Choice | Skill it proves |
|---|---|---|
| Backend | Python, FastAPI, pytest, type hints, ruff | Clean tested Python, APIs |
| Frontend | Next.js, TypeScript, shadcn/ui on a custom token layer | Frontend practice, semantic markup |
| Accessibility | WCAG 2.2 AA target, axe-core in continuous integration | A claim with a check behind it |
| Discovery | Semantic Scholar Academic Graph API with a key | Retrieval over a real corpus |
| Retrieval | A search for 50 Papers, ranked by BM25 and dense vectors in Python and cut to 20, scored against the Retrieval set | Retrieval evaluation, recall at k, nDCG |
| Open copy | OpenAlex resolves open file candidates by digital object identifier; repository locations rank before journal locations under ADR 0012 | Working with a real, broken supply of files |
| Source text | Open copy fetch, PDF and HTML extraction, and a quality detector with a per host success rate | Data engineering on messy input |
| Real world evidence | One web search step for Statistics and Products | Context engineering |
| Storage | Supabase Postgres, with pgvector for the stage 5 chunk search | Vector databases, database design |
| Extraction | Claude Haiku 4.5, one call per chunk | Prompt engineering at volume |
| Drafting | Claude Opus 5, one call per Proposal | Quality where it is the product |
| Guard | Exact and normalised matching initially; fuzzy alignment and rejection-only entailment are measured extensions under ADR 0005 | Guardrails, faithfulness scoring |
| Provenance | Character offsets carried through extraction, normalization, and chunking | Verifiable citations |
| Independence | A coauthor graph rule, and identifier deduplication across three identifier kinds | Graph work, entity resolution |
| Replay | Prompts as versioned files, and a cache keyed by every value that changes the answer | Prompt versioning, repeatable evaluation |
| Evaluation | A frozen labelled set, a rubric, regression tests | Evaluation, the hardest line to fake |
| Tracing | Langfuse free tier, with tokens, cost, and 95th percentile latency for each Stage | Observability |
| Serving | Docker, Render free web service, Vercel for the frontend | Prototype to production |
| Access | One signed Invite code with an expiry, and no `invite` table | Signed values, and storage you do not need |

The Stage runs inside the FastAPI process as a background task, and the page polls for Stage progress with a plain `GET` every 3 seconds. No free tier runs a separate worker process. Fynd uses neither WebSockets nor long polling. A Stage sends one event, which is done or failed, and the page needs the new data in a request anyway, so a socket buys lower latency on a Stage that takes up to 3 minutes. A socket and a held request also keep a worker busy for that whole time on a free tier that runs few workers, and a sleeping container drops the connection, which then needs reconnect code beside the code that already reads the saved state. See [ADR 0003](./docs/adr/0003-four-routes-with-short-polling.md). Stage state is written to the database after every stage, because the free container sleeps after 15 minutes of no requests and can restart mid-run. A scheduled ping keeps the Supabase project awake, because a free project pauses after one week of no activity.

The Render free tier was confirmed on 2026-10-08. It grants 750 instance hours for each workspace in a calendar month, it spins a web service down after 15 minutes with no inbound traffic, and the spin up takes about one minute. That one minute lands on the student before a Stage starts, so the first request of a visit is slow by design. Free Render Postgres expires 30 days after creation, which costs Fynd nothing, because the database is Supabase. Google Cloud Run is the named fallback, with 2 million requests, 180,000 vCPU seconds, and 360,000 GiB seconds free each month, and it scales to zero. Cloud Run needs a billing account, and Render does not, so Render stays for the demo.

Model cost is roughly 240,000 input tokens of extraction plus one drafting call. That is under one dollar per Project.

The runner exposes `run_stage(project_id, stage, run_id)` and owns persistence; Stage rule files retain the separation in ADR 0006. Repeating a completed current run returns saved results without duplicating them. A retry reuses the run identifier; a Re-roll creates a new one. Older runs cannot overwrite newer state, and concurrent invocations must not duplicate committed effects. Version 1 retains one current `stage_run` row per Project and Stage, with no attempt history. This reliability work belongs to the baseline; moving execution to a queue is a separate proposal. Idempotency of saved state does not guarantee exactly one external call or charge. See draft [ADR 0017](./docs/adr/0017-a-stage-run-has-one-current-identity.md).

### Optional AWS demonstration

After the baseline and its measurements, an optional separately deployable SQS/Lambda path may invoke the same runner, with resources described in Terraform, a source-queue dead-letter policy, and a budget alert. The main version 1 deployment stays on FastAPI. The demonstration is complete only when duplicate delivery, retry after interruption, and eventual dead-letter handling have been checked, not merely a successful run. Queue delivery does not guarantee exactly-once work; a dead-letter queue does not repair failures; a budget alert is not a hard spending cap. The database-to-queue handoff, ownership and retry details, resource limits, and spending controls need design before implementation or deployment. No production migration is agreed.

### Optional MCP demonstration

After the AWS stretch item, an optional MCP interface may expose `search_papers` and `verify_claim` using the same underlying Fynd logic. Its purpose is learning and interoperability until a real external application needs it. Return Paper metadata, verified Claims, and verification outcomes, not abstracts or Source passages. Verification may read Source text internally. The interface cannot create Projects, record Picks, request Re-rolls, or start Stages. Enforce those limits in code, not only tool annotations. The transport, client, access controls, and operational limits remain to be designed; no public service or production dependency is required by this decision.

### Continuous integration

Add GitHub Actions checks as their components become runnable: ruff, contract tests, metric 1 replay, verifier measurements, Injection set replay checks, and frontend accessibility scans. Once established as required, these checks must pass before merging. Missing required replay data fails visibly rather than silently skipping evaluation. Tests use committed data permitted by ADR 0011 and call no live paid services. The initial exact/normalised guard needs no downloaded NLI model. If a local model later becomes a required check, CI setup obtains a pinned, permitted model artifact and caches it by its identity/revision; tests must not silently switch models or skip on a missing artifact. The retrieval table remains outside CI under ADR 0013; this decision does not move its uncommitted abstracts into git.

A passing replay checks code against pinned inputs and recorded model answers. A prompt or model change affecting behaviour requires fresh dated evaluation and updated replay evidence before acceptance, even when the old replay still passes. Paid measurements and the LLM judge remain outside routine CI. Metric 2 remains the human review of complete Projects, not an automated judgement inferred from green checks. CI adoption does not authorise automatic deployment.

### Test contracts and pruning

Organise tests around product promises: a Claim maps to its Source span; a rejected Claim never reaches output; duplicate Sources cannot inflate independence; thin evidence cannot create an unsupported Candidate Problem; a Project resumes from saved Stage state after restart; and failed, duplicate, or obsolete runs cannot corrupt Project state. Add missing coverage while building the baseline. Retain useful checks for cache keys, malformed replies, fetching rules, budgets, and known bugs.

Prune incrementally when reviewing the relevant code. Remove a test only when its promise is covered elsewhere, its requirement no longer applies, or it checks an unnecessary implementation detail. Preserve useful regression coverage. A large test count, a reference to an internal function, or many failures after one mutation is a reason to investigate, not proof that tests are redundant. Do not make a wholesale test cleanup a prerequisite for finishing the Stages.

## Design direction

Structure comes from research tools, with Elicit as the reference for showing Claims with citations without drowning the reader. Colour and voice come from warm writing tools, and the empty states and the stage 3 copy carry that warmth, because the student is most uncertain there. Components are standard, so an input box feels like an input box. The theme is not the default: a chosen typeface pair, a chosen colour scale, a 5 step type scale, and one density. Stage 3 shows the 3 candidate Problems as three standard cards side by side, each with its 2 Claims and their citations. The bespoke problem picker was cut on 2026-10-07 to pay for the measured components, and the cards carry the same information in the same order.

## Three week plan

The dated plan below is historical. The current baseline-first build order and the next section-by-section design task are recorded at the top of [NEXT-STEPS.md](./docs/history/next-steps-2026-10.md). No replacement baseline date or experiment time box has been selected.

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

- Two Domains ship instead of three. Technology and Energy ship, and Healthcare is cut. See ADR 0009.
- Stage 3 shows three standard cards instead of one bespoke problem picker.
- The buffer drops from two days to one.

If a day slips, cut in this order. The retrieval table shrinks from five configurations to three, which keeps the baseline, the keyword row and the dense row, and drops the fusion and reorder rows. The independence rule keeps the venue and year check and drops the coauthor graph. The handover export loses its questions list. The evaluation harness and the verifier table ship whatever happens, because without them Fynd is a wrapper around a model.

## Risks

- PDF text extraction returns rubbish for some papers. The buffer on days 19 and 20 exists for this risk.
- The model invents a Claim that no Source states. The citation guard and metric 1 exist for this risk.
- Semantic Scholar allows 1 request per second on search with a key, so stage 4 is slow by design. Cache every fetch on disk from day 1.
- A Problem reads well but a bachelor's student cannot build the Technical core in one year. Metric 2 tests exactly this, and it is the failure that an academic sounding proposal hides.
- Publisher abstracts are not licensed for redistribution. Fynd shows a short quote with a citation, and never republishes a stored abstract in full.
- The seeded Topic is UK household energy forecasting. Pick a second Topic only after metric 1 and metric 2 pass on the first.

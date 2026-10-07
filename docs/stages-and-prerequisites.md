# The seven Stages, and what to learn for each one

Updated: 2026-10-06. For Deshan.
Read [CONTEXT.md](../CONTEXT.md) for the words and [PRD.md](../PRD.md) for the scope.
A personal study document outside the repository defines each concept named here.

This document has two jobs. It states what each Stage does and what each Stage saves. It also lists the subject you must know before you build that Stage.

Nothing here changes the scope. If this document and `PRD.md` disagree, `PRD.md` wins.

## How to read the Stage sections

Each Stage section has four lines.

- The student does: the one action the student takes.
- Fynd does: the work Fynd runs for that action.
- Stage state: what Fynd writes to the database before the Stage ends.
- Learn first: the subjects you must know to build it.

## Stage 1: pick a Domain

The student does: picks one Domain from Technology, Healthcare, or Energy.

Fynd does: creates the Project, saves the Domain, and mints the secret link.

Stage state: the Domain, the Project identifier, and the created time.

Learn first:

- A closed set of valid values, and why a free text field is a different design.
- Pydantic models for request and response validation.
- One Postgres table, one row, and a primary key.

## Stage 2: pick a Topic

The student does: picks one Topic from the 5 to 8 that Fynd proposes.

Fynd does: asks a model for Topics inside the Domain, then runs a count check on the picked Topic.

Stage state: the proposed Topic list, the picked Topic, and the count check result.

Learn first:

- Prompting a model for a list, and why you ask for a fixed shape.
- Structured output, which means the model returns JSON that matches a schema you define.
- Generate then verify, which means the model proposes and your code checks the proposal against a real source.
- The Semantic Scholar search endpoint, and the 1 request per second limit.

## Stage 3: pick a Problem

The student does: reads 3 candidate Problems with their early evidence, and picks one.

Fynd does: drafts 3 Problems inside the Topic, and attaches the early evidence for each one.

Stage state: the 3 candidate Problems, their evidence, and the picked Problem.

This Stage earns the product. Spend the most design time here.

Learn first:

- One web search step for a Statistic or a Product, because a Paper alone does not prove the Problem is real.
- Writing a prompt that must cite, and rejecting output that does not.
- Why a Problem that already has solutions is still a good Problem. See [ADR 0001](./adr/0001-real-world-problem-with-literature-as-evidence.md).

## Stage 4: build the Shortlist

The student does: keeps the Sources that look relevant, and drops the rest.

Fynd does: searches for Sources, fetches the open full text, and shows the titles and abstracts.

Stage state: every fetched Source, and the keep or drop decision for each one.

Learn first:

- Calling a REST API with pages of results.
- Rate limiting, and why you wait between requests instead of retrying fast.
- Caching a response on disk, so the second run costs nothing.
- Fetching a PDF and extracting its text, and why some PDF files return rubbish.
- Finding the same Paper twice under two identifiers, and keeping one copy.

## Stage 5: deep read the Shortlist

The student does: reads the Claims, the Existing approaches, and the Gap.

Fynd does: splits each Source into chunks, extracts Claims, groups the Existing approaches, and names the Gap.

Stage state: every Claim with its citation, every Existing approach, and the Gap.

This Stage is the one you asked about. Chunking, embedding, storing, and retrieving is retrieval augmented generation, and people call it RAG.

Learn first:

- Chunking, which means cutting a long text into pieces small enough for one model call.
- Embeddings, which means turning a chunk into a list of numbers that carries its meaning.
- Vector search with pgvector, and why cosine distance finds a near meaning.
- RAG, which means you retrieve the chunks first and put them in the prompt.
- The citation guard: a Claim must appear in its Source text, or you drop the Claim.
- Clustering, because a Gap is the shortcoming that several Existing approaches share.
- The evidence bar: 3 or more Claims from independent Sources, with at least one Paper and at least one Statistic or Product.

## Stage 6: draft the Proposal

The student does: accepts the Proposal, or asks again.

Fynd does: drafts one Proposal that answers the Gap, with a Technical core and a Point of difference.

Stage state: every drafted Proposal, and the accepted one.

Learn first:

- A long prompt that carries the Gap, the Claims, and the Existing approaches.
- Why every Proposal must name a Technical core and cite the Source it comes from.
- An evaluation plan with a baseline, because a Proposal without one cannot be marked.

## Stage 7: export the handover

The student does: downloads the handover.

Fynd does: renders the Problem, the evidence, the Gap, the Technical core, the features, the references, and the questions.

Stage state: the export and its created time. The PRD forbids a revision after export.

Learn first:

- A template that turns stored rows into a document.
- A numbered reference list that matches the citations in the text.

## Subjects that cross every Stage

These subjects do not belong to one Stage. You need them from day 12.

- A background task inside the FastAPI process, and a page that polls for progress.
- Saving Stage state after every Stage, because the free container sleeps after 15 minutes.
- Idempotency, which means a Stage that runs twice leaves the same result.
- Tracing with Langfuse, and the cost of one Project.
- A frozen labelled set, a rubric, and a regression test that fails when grounding drops.
- WCAG 2.2 AA, axe-core in continuous integration, and one keyboard only pass.

## The order to learn them in

1. REST APIs, rate limits, and the disk cache. Stage 4 needs these first.
2. PDF text extraction. Still Stage 4.
3. Chunking, embeddings, pgvector, and RAG. Stage 5 needs these.
4. Structured output and the citation guard. Stage 5 and Stage 2.
5. Prompting for Problems and Proposals. Stage 3 and Stage 6.
6. The labelled set and the regression tests. Days 9 to 11.
7. FastAPI, the background task, and Stage state. Days 12 to 14.

This order matches the three week plan in `PRD.md`.

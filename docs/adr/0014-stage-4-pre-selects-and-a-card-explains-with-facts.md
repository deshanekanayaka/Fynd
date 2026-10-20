---
status: accepted
date: 2026-10-20
---

# Stage 4 pre-selects the Shortlist, and a card explains with facts

Stage 4 shows every Paper of the top 20 with the keeps already ticked, and the student overrides any of them. The Shortlist is capped at 10 Papers. Each card carries one line built from facts, which names the matched terms, the year, and the full text status. No model writes that line.

The Pick stage 4 accepts is the Shortlist itself, which is one item of the type Shortlist. See [ADR 0006](./0006-a-stage-offers-then-accepts.md) and [ADR 0003](./0003-four-routes-with-short-polling.md). No new route and no new word appear.

## Why the student still picks

Fynd could screen alone. The retrieval table would then be the only evidence that the screening was right, and one known finding argues against it. The `query` the model writes is unmeasured, so a bad search is possible, and stage 4 is the one screen where a student would see it.

The student is not carrying the teaching load here. `PRD.md` holds that stage 3 is where the student learns the lesson, and that stage 1 and stage 2 are dropdowns. A pre-ticked list lets a student click through and still reach a sensible Shortlist.

## Why the line holds no written sentence

Every generated sentence in Fynd is guarded, because a Claim must appear in its Source text. A justification is prose about a Paper and not a Claim, so it would be the first ungrounded sentence Fynd shows a student, at 20 model calls and real latency, with no number behind it.

The retrieval step already knows why each Paper ranked where it did. A term match names its stems. A meaning match says that the meaning is close with no exact term match, which is the clearest explanation of dense retrieval a student will meet, at the moment it matters.

## Why the full text status arrives late

The measured runs say 5 of 20 Papers reach Usable text, so most cards name a Paper stage 5 cannot read. A student who shortlists those watches stage 5 return almost nothing.

The status cannot be known when the screen opens. One Paper allows 3 fetch attempts, each with a 30 second timeout and a robots wait, so 20 Papers run far past the 3 minute rule of metric 3. No measurement file records elapsed time yet, which is its own gap.

So the screen opens with the ranking, the year and the matched terms, which are free, and each full text status fills in as its Paper resolves. The 3 second polling of ADR 0003 already carries it, and no route changes. Nothing is pre-ticked until its status is known, and a student can tick a Paper before then.

## Consequences

The screen states the count in one sentence, for example "5 of 20 Papers have a full text Fynd can read". That is a measured number, and it is the plainest signal a student gets that the open access supply is broken.

The Shortlist cap of 10 protects metric 3, because stage 5 runs one model call per chunk.

`accept` checks every identifier in the Shortlist against the offered list, which is the rule ADR 0006 already states.

The `Shortlist` entry in `CONTEXT.md` gains one sentence saying it is the Pick stage 4 accepts.

The measurement command gains elapsed time per Paper and a total, because metric 3 has no evidence behind it for this Stage.

## Considered options

Fynd screens alone and shows the Shortlist it chose. Rejected because the untested `query` means a bad search is possible, and this is the one screen where a student would catch it.

The student screens alone from an ordered list with no pre-tick. Rejected because a student with no research training has no rule to screen by, which is the problem Fynd exists to solve.

One model written sentence under each Paper. Rejected for the guard, the cost and the latency. It returns when it has a guard and a number of its own.

Hide the Papers with no Usable text. Rejected because it shows a student 5 cards and teaches that screening is trivial, and it hides a true finding about open access.

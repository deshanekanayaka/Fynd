# Answering "how long would a team take to build this?"

Updated: 2026-10-07. For Deshan, to use in a room.

An investor asked this at a university event. It is a test, not an attack. He wants to find out whether you know which part of your own project is hard. Read [PRD.md](../PRD.md) for the numbers this document points at.

## The answer, in four sentences

A good team rebuilds the product in four to six weeks.

What they cannot buy in four to six weeks is the evidence that it works. That evidence is a hand labelled set, a threshold table, and a retrieval evaluation on labelled data.

Fynd finds 90 percent of the true Claims and invents none, and the test runs in front of you.

Without that evidence a team ships something that demos the same way and fabricates a citation in week two, and nobody notices until a supervisor does.

## Why this answer works

It gives him a real number first. A person who will not name a number looks like a person who never estimated one.

It then moves the question from the code to the data. The pipeline is the half that money buys quickly. The labelled set, the thresholds, and the measurement are the half that takes a person reading papers, and the hours do not compress.

It names the failure mode he already fears. Two systems look identical in a demo, and one of them invents evidence. He cannot tell them apart by looking, and neither can his developers, which is the point.

## The numbers to quote

Quote only what the repository produces, and name where it lives.

- Claim extraction: recall and invention rate on a frozen labelled set of 10 Sources, run in continuous integration.
- The citation guard: precision and recall at each threshold, with the chosen operating point written down.
- Retrieval: recall at 20 and nDCG for four configurations, on 40 to 60 hand labelled Papers.
- Full text extraction: the share of Papers that give usable text, for each host.
- Every Stage: tokens, cost, and 95th percentile latency.

## The follow-up questions, and the answers

"So the code is not the value?" Correct. The value is the measurement, the labelled data, and the fact that a supervisor accepts the output. Any team writes the pipeline, and no team starts with the numbers.

"Could a model do the labelling?" Not for the set that grades the model. A labelled set written by the same kind of model it grades measures agreement, not truth. That is the mistake the guard exists to avoid, which is why the entailment tier runs a local model and only ever rejects.

"What stops a competitor?" Not the code. The labelled data, the evaluation record, and the relationship with the departments whose supervisors accept the handover. Say that plainly.

"How would you spend money on this?" On labelling and on a second Domain, in that order, because both are human hours and both move the numbers that matter.

## What not to say

Do not say the project is complex. Complexity is not a selling point and it invites him to ask which part, which you then have to defend.

Do not say it cannot be copied. It can. The person asking knows that, and a naive answer ends the conversation.

Do not quote a number the repository does not produce. One unsupported figure costs you every supported one.

## The same question in an interview

An interviewer asking "could I do this with ChatGPT?" is asking a different question. They want to know whether you know where the engineering is. The answer names the components that carry numbers, which are retrieval scored on your own labelled set, faithfulness scoring with a tuned threshold, prompt versioning with replayable runs, entity resolution for Source independence, and idempotent Stage execution on a container that sleeps. Then give one number and offer to show the test.

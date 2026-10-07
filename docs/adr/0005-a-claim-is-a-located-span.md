---
status: accepted
date: 2026-10-07
---

# A Claim is a located span, and the entailment tier only rejects

A Claim is stored as a slice of the Source text. The model locates the Claim, and the Source supplies its words. A `claim` row holds the start and the end character offset, the slice between them, the hash of the text those offsets were measured against, the tier that located it, and that tier's score.

The verifier runs four tiers in order. The first three locate a span, and the fourth is a gate on meaning.

1. Exact match against the Source text.
2. Normalized match, after case folding, unicode normalization, and dehyphenation.
3. Fuzzy alignment, with a token level score over a sliding window.
4. Entailment, with a small natural language inference model, which decides whether one sentence implies another.

Tier 4 can only reject. A Claim that no locator can place in the text is dropped, and no tier can admit a Claim that the Source does not contain.

The operating point is the lowest tier 3 threshold that invents nothing on the labelled set. Day 6 publishes precision and recall at every threshold, with one sentence saying why the chosen row was chosen.

A dropped Claim is counted, with the reason and the tier that refused it. The counts are a file in the repository and the source of the rejection histogram.

## Consequences

The project rule in `AGENTS.md` holds without an exception. A Claim must appear in its Source text, and the table has nowhere to put one that does not.

The fuzzy tier is a locator and not a softener. Its score says how confident the match is, and a loose match that reverses the meaning of the sentence is still rejected by tier 4.

Precision matters more than recall here, and the chosen operating point says so. Metric 1 asks for 90 percent of the true Claims and zero inventions. One invention in a handover destroys the one promise Fynd makes, and a missed Claim costs the student one line of evidence out of several.

The entailment model runs locally, so the guard never asks one commercial model to grade another. That answer matters in an interview as much as in the code.

Offsets place a real cost on the text pipeline. Extraction, unicode normalization, dehyphenation, and chunking each move characters, so each step returns an offset map beside the text and the pipeline composes those maps. One test takes a Claim offset back to the raw file and reads the same sentence.

## Considered options

Storing the sentence the model returned, with a note that it matched. Rejected because the stored text is then the model's wording, and a reviewer has no way to read the same characters in the paper.

Letting tier 4 accept an implied Claim with a flag, as the architecture review proposed. Rejected because it contradicts `AGENTS.md` and `CONTEXT.md`, where a Claim is one sentence from one Source. A flag that marks a Claim as not quite quoted is the softening that rule exists to prevent.

A single exact match, which is the design before this entry. Rejected because real text defeats it. A model writes "don't" for "do not", an extractor leaves a ligature, and a line break splits a hyphenated word, so true Claims get dropped and metric 1 falls for no good reason.

Choosing the threshold by the best balance of precision and recall. Rejected because the two are not equally valuable to Fynd, and metric 1 already states the asymmetry.

Dropping a failed Claim silently. Rejected because the count tells you whether a low metric 1 comes from a weak prompt or a strict threshold, which is the first question anyone asks when the number disappoints.

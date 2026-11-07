---
status: accepted
date: 2026-10-07
---

# A Claim is a located span, and the entailment tier only rejects

A Claim is stored as a slice of the Source text. The model locates the Claim, and the Source supplies its words. A `claim` row holds the start and the end character offset, the slice between them, the hash of the text those offsets were measured against, the tier that located it, and that tier's score.

The designed extension path has four tiers in order. The first three locate a span, and the fourth is a gate on meaning. The initial implementation uses exact and normalised matching only; the last two tiers require a later measured justification.

1. Exact match against the Source text.
2. Normalized match, after case folding, unicode normalization, and dehyphenation.
3. Fuzzy alignment, with a token level score over a sliding window.
4. Entailment, with a small natural language inference model, which decides whether one sentence implies another.

Tier 4 can only reject. A Claim that no locator can place in the text is dropped, and no tier can admit a Claim that the Source does not contain.

## Clarification agreed 2026-11-07: the entailment inputs

The entailment check compares the actual Source passage found by the locator with the wording proposed by the extraction model. It asks whether that passage supports the proposed wording. It does not compare the stored Source sentence with itself. For example, a located passage saying a model "did not improve forecasts" must not support proposed wording saying it "improved forecasts".

The check can reject the extraction, but cannot admit an unlocated Claim. A passing Claim still stores the Source's actual sentence and character positions, never the extraction model's altered wording. This check addresses meaning changes during extraction or matching; it proves neither the Source's factual truth nor the support for a whole Candidate Problem.

Measure exact and normalised matching first. Publish their results and disclose whether metric 1 passed before investing in later tiers. Fuzzy matching is tested on true Claims the first two tiers missed and deliberately incorrect matches, including meaning reversals. Choose a threshold on development examples, then check it on separate evaluation examples. If recovery is not worthwhile or no evaluated setting avoids incorrect admissions, omit fuzzy matching. The minimum worthwhile gain is not yet fixed. Zero measured mistakes is not a guarantee on unseen Sources. This is an implementation and measurement sequence, not permission to weaken the located-span rule.

## Final review clarification, 2026-11-07

The extraction-wording entailment check has a purpose where fuzzy alignment can locate similar wording with a changed meaning. With only exact and normalised matching, do not add a redundant comparison merely to include an NLI model. The separate model study now targets Claim-to-Problem support after grouping, not this citation check. That study starts offline after the baseline; neither it nor its LLM judge is a production gate by this decision. Applying a support model to the later Gap needs a separate definition and evaluation.

## Operating point

If tier 3 is retained, the operating point is the lowest tested threshold that admits no incorrect matches on development data and remains acceptable on separate evaluation. Publish precision and recall at the tested thresholds and explain the chosen row. The original day 6 schedule is historical; no threshold or result is implied by this record.

A dropped Claim is counted, with the reason and the tier that refused it. The counts are a file in the repository and the source of the rejection histogram.

## Consequences

The project rule in `AGENTS.md` holds without an exception. A Claim must appear in its Source text, and the table has nowhere to put one that does not.

The fuzzy tier is a locator and not a softener. Its score measures similarity, not the probability of correctness. Test that meaning reversals are rejected by the complete retained guard, including the entailment gate if fuzzy matching is used.

Precision matters more than recall here, and the chosen operating point says so. Metric 1 asks for 90 percent of the true Claims and zero inventions. One invention in a handover destroys the one promise Fynd makes, and a missed Claim costs the student one line of evidence out of several.

If the citation entailment tier is retained, its model runs locally, so the production guard never asks one commercial model to grade another. Check peak memory, startup and inference against verified hosting limits before selecting the model. No model or presumed memory allowance is adopted here. The README must distinguish this production boundary from the offline LLM-judge experiment.

Offsets place a real cost on the text pipeline. Extraction establishes the Source text; unicode normalization, dehyphenation, and chunking can move characters, so those transformations return offset maps and the pipeline composes them. One check takes a Claim offset back to the Source text and reads the same sentence, not positions in PDF bytes. See ADR 0007's correction.

## Considered options

Storing the sentence the model returned, with a note that it matched. Rejected because the stored text is then the model's wording, and a reviewer has no way to read the same characters in the paper.

Letting tier 4 accept an implied Claim with a flag, as the architecture review proposed. Rejected because it contradicts `AGENTS.md` and `CONTEXT.md`, where a Claim is one sentence from one Source. A flag that marks a Claim as not quite quoted is the softening that rule exists to prevent.

A single exact match, which is the design before this entry. Rejected because real text defeats it. A model writes "don't" for "do not", an extractor leaves a ligature, and a line break splits a hyphenated word, so true Claims get dropped and metric 1 falls for no good reason.

Choosing the threshold by the best balance of precision and recall. Rejected because the two are not equally valuable to Fynd, and metric 1 already states the asymmetry.

Dropping a failed Claim silently. Rejected because the count tells you whether a low metric 1 comes from a weak prompt or a strict threshold, which is the first question anyone asks when the number disappoints.

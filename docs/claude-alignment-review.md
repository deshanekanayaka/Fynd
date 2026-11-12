# Claude review: final disposition

Review closed: 2026-11-07. Deshan supplied Claude's final response and asked for the discussion to end and the documents to be updated. This file replaces the earlier copy-ready review prompt. No further Claude review is required to record these decisions.

This is a review record, not the source of product scope or permission to implement. Read [PRD.md](../PRD.md), [CONTEXT.md](../CONTEXT.md) and the final review at the top of [NEXT-STEPS.md](./history/next-steps-2026-10.md) for the current direction. Historical build entries retain their dates.

## Incorporated conclusions

- Complete and measure the baseline first, including quarantine, a small injection check, saved Stage state, tracing, CI and accessibility. The live journey, README measurements, refusal example and reviewed Projects are explicit completion criteria in PRD.md. Baseline date and individual experiment time boxes remain TBD.
- The post-baseline LangGraph agent will be built and measured within a time box. Production adoption alone is conditional. Compare it with the fixed sequence and explicit recovery rules, publish the outcome, and retain simpler production rules if they win.
- The initial citation verifier uses exact and normalised matching. Fuzzy recovery and its rejection-only entailment check are measured extensions. The located-span rule never changes.
- The model comparison instead targets Claim-to-Problem support after grouping. Start offline with a small feasibility pilot; a future production check would precede the cards. The pilot cannot establish model superiority or production accuracy.
- Candidate hard negatives may come from other Candidate Problems in the same Topic, but a swapped pair is not automatically negative. Report easy cross-Topic negatives separately. Deshan labels before seeing predictions, uncertain examples and exclusions are reported, and no large annotation task is assumed.
- SciFact can support a learning/training experiment, but its scientific statements and abstract evidence differ from Fynd's inputs. No transfer improvement or decrease is asserted without measurements. Training, development and final evaluation need separation by Source and related Problem where appropriate.
- Before choosing or training local models, measure peak process memory, loading and inference in the verified target environment. The LLM judge remains a manually measured competitor, not a production gate or the grading authority.
- Preserve the idempotent runner contract, optional AWS/MCP demonstrations, required accessibility, offline CI replay and incremental contract-test pruning.

## Corrections to the supplied review

Claude could not inspect the latest local changes. Its statement that the ADR 0005 clarification was absent was therefore not a verified fact: the dated clarification already existed locally. It is now expanded to identify the initial configuration and the separate support study. See [ADR 0005](./adr/0005-a-claim-is-a-located-span.md).

The inference that the same model check can validate the later Gap is not adopted. A Claim may support only part of a multi-part Candidate Problem, and a Gap concerns shared shortcomings across independent Sources. Define partial support before the pilot; evaluate Gap support separately before any reuse. The baseline still relies on the human rubric under [ADR 0008](./adr/0008-stage-3-groups-claims-it-already-holds.md).

The estimates of about 15 Candidate Problems, about 30 positive pairs and about 60 total pairs from 5 Projects are planning illustrations, not guaranteed counts or approved annotation requirements. Thin evidence and repeated Sources change those counts. The proposed plus/minus uncertainty margin is not a recorded statistical result, and close model rankings cannot be claimed from the pilot.

No model-family memory claim is adopted. A presumed 512 MB allowance, predictions that a particular family will fit, and the estimated afternoon needed for a preflight remain unverified. Verify deployment limits and measure the actual process before selecting a model.

Stage 3 failure analysis must use Candidate Problem requirements, not the later Gap's separate evidence bar. About 10 exploratory Topics is a suggested starting scope, not a final evaluation or a requirement to label another large dataset.

An initial exact/normalised verifier does not need an NLI download in CI. If a local model later becomes required, setup obtains a pinned, permitted model artifact and caches it by identity/revision. A missing artifact fails visibly; it does not justify switching models or silently skipping a gate.

## Remaining design work

Resume the section-by-section process with the product/scope changes (Section 2), then non-functional requirements (Section 3). No separately named Section 2/3 draft was found locally, so no completed draft is claimed. PRD.md contains named placeholders for the baseline date, spending limit, tool-call unit and cap, token cap, execution budget, fuzzy threshold, model memory allowance and experiment time boxes.

Also resolve active computation versus waiting for a student's Pick, ownership of concurrent attempts of the same logical run, atomic commits, and runtime cache durability. A run identifier alone does not solve these. The older database five-minute rule is explicitly flagged for revision before implementation; see [database design](./database-design.md) and [draft ADR 0017](./adr/0017-a-stage-run-has-one-current-identity.md).

The recorded build order is Claim set, extraction and initial verifier, fixed Stage 3 with quarantine/injection checks, runner/persistence, Stages 4 to 7, frontend/accessibility, complete tracing and CI, deployment and reviewed Projects, then time-boxed experiments. Add checks and tracing alongside their components rather than deferring all verification until the end.

## Status

The discussion is closed; implementation design is not complete. [ADR 0016](./adr/0016-source-passages-stay-outside-the-agent.md) and [ADR 0017](./adr/0017-a-stage-run-has-one-current-identity.md) remain proposed drafts. No agent, trained model, AWS hosting migration or MCP service is adopted for production. No code, infrastructure or deployment was created in this documentation session. Interview readiness will be addressed separately.

---
status: proposed
date: 2026-11-07
---

# A Stage run has one current identity

Expose `run_stage(project_id, stage, run_id)` in the runner and keep one current run identifier on each Project/Stage pair. Retrying interrupted work reuses that identifier; a Re-roll replaces it. This lets the runner recognise repeated work and reject obsolete completions without adding an attempt-history table that no current product flow reads.

## Contract

The runner owns saving and the Stage sequence, preserving ADR 0006. FastAPI calls it as an in-process background task for version 1. Any later queue integration calls the same entry point and must meet the same contract.

A completed current run returns its saved result when repeated. Concurrent invocations must not duplicate committed effects. A run that is no longer current cannot overwrite the current run or Stage state. The Stage result and completion state must be committed consistently so a failure cannot expose a half-finished result as complete.

The current-run identifier is added to `stage_run`; the primary key remains the Project/Stage pair. A Re-roll replaces that current row rather than appending history. Atomic ownership, commit checks, and recovery after a process stops require an implementation design and checks before code is written. In particular, checking the identifier once at startup is insufficient: it can become obsolete while external work is running.

## Trade-off and limits

Before implementation, distinguish active computation from waiting for a student's Pick. The older five-minute rule in the database design cannot fail a Project merely because the student is still deciding. Define ownership of concurrent attempts of the same logical run as well: they share `run_id`, so that identifier alone cannot prevent an obsolete attempt from committing. Ownership and timeout mechanisms remain to be designed rather than implied by the schema.

Keeping every attempt would help historical inspection but adds storage and lifecycle rules not used by version 1. Keep only the current run in this table. This is not a claim that traces or external fetch caches must be deleted.

Idempotency protects saved Project state, not exactly-once execution of paid external calls. A process can stop after receiving a model answer but before caching it, so a retry may pay again. The cache reduces repetition but does not close that crash window.

This draft records the agreed persistence boundary and contract, not an adoption of Lambda, SQS, or a separate worker. The background task remains inside FastAPI.

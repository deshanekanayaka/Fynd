---
status: accepted
date: 2026-10-07
---

# Four routes, 202 Accepted, and short polling

Fynd exposes four routes for all seven Stages. `POST /projects` creates a Project and saves stage 1. `POST /projects/{secret_link_id}/picks` records one Pick. `POST /projects/{secret_link_id}/re-rolls` asks one Stage to run again. `GET /projects/{secret_link_id}` reads the Project.

The create returns `201 Created`. A Pick and a Re-roll return `202 Accepted`, because each one starts the next Stage as a background task and returns before it finishes. All four routes return the same Project document, so a caller learns one shape.

The page then polls the `GET` route with a plain request every 3 seconds until the Stage is done. Fynd uses neither WebSockets nor long polling.

A Re-roll is a `POST` because it writes a new `stage_run` row, raises the round, drops the old `stage_state` row for that Stage, and spends model tokens. A `GET` must be safe to repeat and safe to cache, and a browser or a proxy can fetch one without the student asking.

## Consequences

The rule for which Stage runs next lives on the server and nowhere else. The Pick body names the Stage it answers and never names a Stage to run, so neither the frontend nor the command line holds a copy of the seven Stage sequence.

One Pick route serves every Stage, and the body shape changes with the Stage. `stage_number` is the discriminator, stage 2 names a Topic slug, and stage 3 names a `candidate_problem_id`. The specificity sits in the field names, which follow `CONTEXT.md`, and not in the route name. FastAPI renders that union on its documentation page as one endpoint with a named variant per Stage.

Polling costs about 60 reads of one document for a 3 minute Stage. The document holds the Project, the Stage payloads, the candidate Problems, and their Claims, and the last read is the one that carries the new data. A separate small status route is the next step if a measurement shows the body hurts, and not before.

The state of a running Stage reaches the page as a `run` object inside the Project document, holding the Stage number, a state of `running`, `failed`, or `done`, the started time, and an error message. There is no separate route for that state.

## Considered options

One route for each Stage, seven in total. Rejected because the caller then knows which route belongs to which Stage, which puts the Stage sequence in the frontend and in the command line as well as on the server.

A route for each kind of Pick, for example `topic-picks` and `problem-picks`. Rejected for the same reason, and because one word with one meaning is the rule in `CONTEXT.md`. A Pick is a Pick whatever was picked.

WebSockets. Rejected because a Stage sends one event, the page needs the new data in a request anyway, a socket holds a worker for up to 3 minutes on a free tier that runs few workers, and a sleeping container drops the connection, which then needs reconnect code beside the code that reads the saved state. The PRD also lists response streaming as a non-goal.

Long polling. Rejected for the worker cost above, and because Fynd has no pub/sub, so the server then polls its own database inside a held request. The gain is arriving 3 seconds sooner on a Stage that takes up to 180.

A fifth route that returns the run state alone. Deferred, not rejected. It is the first thing to add when the document size is measured and found to hurt.

---
status: accepted
date: 2026-10-08
---

# A Stage offers, then accepts, and the runner does the saving

A Stage is two named jobs in one file. `offer` produces what the student chooses from. `accept` takes the Pick and refuses a Pick that the Stage never offered.

A Stage file holds the rules of that Stage and nothing else. It knows nothing about HTTP, nothing about the command line, and nothing about Postgres. It receives values and returns a result.

A Stage receives its search and its model as plain function arguments, typed as callables, with no default values. The edge wires the real ones. For stage 2 the two jobs read:

```
offer_topics(domain, ask_model) -> list of offered Topics
accept_topic(pick, offered, search) -> what it decided
```

One other file, the runner, writes `stage_run` and `stage_state`, and knows the order of the seven Stages. The runner calls `offer`, saves the offered list in the `stage_run` `detail` column, and waits. When the Pick arrives, the runner reads that saved list and calls `accept` with it. If the answer keeps the Pick, the runner writes `stage_state`.

`accept` checks the Pick against the stored offered list, and never against a list the caller sent. The secret link is the only access control, so a caller can send any value it likes.

`accept` returns what it decided, and does not raise for a normal outcome. Stage 2 decides one of three things. The Topic is kept. The Topic is below the open Paper threshold, with the count. The Topic was never offered.

Each answer is its own small class, and `accept` returns the union of them. Stage 1 returns `DomainKept` or `DomainNotOffered`. One class with a field that means nothing half the time was rejected, because a refusal carries no Domain.

`accept` runs the search itself. The threshold of 3 Papers with an open copy is a rule of the Stage.

## Consequences

Stage 2 has two moments and not one, so the split is the shape of the problem and not a preference. The offered list reaches the database before the student answers, because the free container sleeps and the student reloads. See [ADR 0002](./0002-topics-are-generated-then-verified.md).

Every rule in Fynd is testable with no network, no token spend, and no Postgres. A test passes a fake search function and a fake model function, both of which return a fixed list.

A second kind of test replays a real run from the committed disk cache of [ADR 0004](./0004-replayable-runs-and-versioned-prompts.md). That test proves the real code path with no API key. It arrives with the labelled set, because the cache files come from the same work. The fake-function tests cover days 3 and 4 alone.

The file a reviewer opens to understand stage 2 holds only stage 2. The Stage sequence stays in the runner. That matches [ADR 0003](./0003-four-routes-with-short-polling.md). The Pick names the Stage it answers, and never names the Stage to run.

A Topic below the threshold is not a failed run. The `stage_run` state stays `running`, the count goes in `detail`, and the student picks again. The route turns a never-offered answer into a 4xx reply.

The cost is one more file than a single `run_stage_2` function, and one more hop for a reader to follow.

## Considered options

A class for each Stage, with the search and the model as constructor arguments. Rejected because one interface with one implementation is weight with no payoff, and a plain function argument teaches the same fundamental.

A protocol with a real implementation and a fake implementation. Rejected for the same reason. A fake is a function of three lines in the test file.

Default argument values that point at the real search and the real model. Rejected because a test that forgets to pass a fake then reaches the network and spends tokens, and the mistake is silent.

Patching the search and the model inside the test. Rejected because the test then depends on a name inside the file under test. A rename breaks the test for no reason.

One `run_stage_2` function. Rejected because it must write the offered list to the database halfway through itself, which puts Postgres inside the file that holds the rules.

The runner runs the search and hands the count to `accept`. Rejected because the threshold rule then lives outside the Stage file, and the runner grows one branch for each Stage.

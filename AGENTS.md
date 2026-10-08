# Fynd: agent instructions

Fynd helps a final year project student start from a real problem with evidence, instead of from an app idea. The user is Deshan. He builds this to demonstrate machine learning and AI engineering skill for junior roles, and the ship date is 2026-10-26.

## Read these first, every session

1. [CONTEXT.md](./CONTEXT.md) is the glossary. It is the source of truth for every domain word.
2. [PRD.md](./PRD.md) is the product. Scope, success metrics, non-goals, the stack, and the three week plan.
3. [NEXT-STEPS.md](./NEXT-STEPS.md) is the current state and the immediate task.
4. [docs/adr/](./docs/adr/) holds the decisions and the reasons behind them.

Read all four before you propose work. Do not infer the design from the code, because the code is behind the documents.

## Rules

Use the words in `CONTEXT.md` exactly. A Source is not a reference. A Problem is not a use case. A Claim is not an insight. If the code and the glossary disagree, say so and ask which one is wrong.

Do not add a feature that the PRD lists as a non-goal. Ask first.

Every Proposal names a Technical core and cites the Source it comes from. This rule is the product. See ADR 0001.

A Claim must appear in its Source text. If the check cannot find it, drop the Claim. Never soften this guard to make an output look better.

Cache every external fetch on disk from the first run. Semantic Scholar allows 1 request per second on search with a key.

Write the smallest thing that works, and leave one runnable check behind it. The user is learning, so prefer plain loops and clear names over clever code, and write comments that say why and not what.

The user does not write CSS by hand and has no design training. Use shadcn/ui components with the project token layer. Do not hand write components, and do not ship shadcn defaults.

A docstring opens with one short line in the third person, for example "Greets the user by their name." A function says what it does. A class names what the value is. An exception says when it is raised. The reason goes in a comment beside the code it explains, and not in the docstring.

A pull request opens with a one or two line statement of what it is. Write that line first, in plain words, before any section. A reader who stops after the first line still knows what the pull request does.

## Decisions you must not reverse without asking

- The Problem comes from the real world. Papers are evidence, not the source of the idea.
- No accounts. A signed Invite code and a secret Project link.
- The background job runs inside the FastAPI process. No free tier runs a separate worker.
- Stage state is saved after every stage, because the free container sleeps and restarts.

## Update discipline

When a decision changes, change the document in the same session. A new term goes in `CONTEXT.md`. A changed scope goes in `PRD.md`. A finished task goes in `NEXT-STEPS.md`. A decision that is hard to reverse gets an ADR in `docs/adr/`.

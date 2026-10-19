# Outside references

Projects and APIs Fynd read for ideas, with the link, the licence, and what Fynd took.

Before you copy a line of code, read the licence column. Fynd is a public repository. A repository with no licence file grants no permission to reuse its code, so Fynd reads those for ideas only. See [ADR 0011](./adr/0011-the-public-repository-holds-the-text-and-not-the-files.md) and [ADR 0012](./adr/0012-an-open-file-is-a-licence-question.md).

## Repositories

| Project | Link | Licence | Read on |
|---|---|---|---|
| LangChain Agent Evaluation System | https://github.com/Mohamad-Hachem/LangChain_Agent_Evaluation_System | None stated | 2026-10-19 |
| ai-teammates | https://github.com/code-with-antonio/ai-teammates | None stated | 2026-10-19 |
| Roam, an Airbnb clone | https://github.com/jsmastery-pro/airbnb-clone | MIT | 2026-10-19 |

### LangChain Agent Evaluation System

A learning lab for agent evaluation. It holds a LangChain refund agent, 8 golden cases, 7 DeepEval metrics, and one model judge for each metric.

It states no licence, so Fynd copies no code from it.

Four of its seven metrics do not apply. Task completion, step efficiency, plan quality and plan adherence score a plan an agent chose for itself. A Fynd Stage chooses no tools and makes no plan, because ADR 0006 fixes the order in code.

What Fynd takes.

- The Golden. The expected answer is written down before the run, and the actual answer joins it after. The labelled set of 10 Sources needs this shape.
- A judge returns a score and a reason, and a reader reads the reason before changing code.
- An average and a pass rate answer different questions. One of its metrics averages 0.62 and passes 2 of 8 cases.
- The date warning. Its sample dates are fixed while its date tool reads the machine clock, so a correct answer disagrees with the reference answer. `first_year_in_window(today)` gives Fynd the same hole.

What Fynd refuses. Every judge metric spends a token on every run. No Fynd test reaches the network and no Fynd test spends a token. A judged number belongs in a command a person runs, which writes a dated file.

### ai-teammates

A Next.js and TypeScript project, for personal study at a later stage. It is not an architecture to copy. Its stack is Clerk accounts, Neon, Drizzle, Trigger.dev, Daytona sandboxes and Sentry. ADR 0009 settled on no accounts and one signed Invite code, so Clerk undoes a closed decision.

What Fynd takes. Its use of the Vercel AI Elements component set, and its avatar choice. It draws avatars with `@dicebear/core` and `@dicebear/styles`, and animates with `@rive-app/react-webgl2`. DiceBear generates an avatar from a seed string, so an avatar costs no asset, no designer and no file in this repository. A Project secret link is a seed already to hand. Rive needs an artist and a runtime.

### Roam, an Airbnb clone

An iOS and Android app where a user describes a stay in plain words and the app finds it. It is MIT licensed, so Fynd can use its code and not only its ideas. Its build steps live in its own `prompts/` directory, and `prompts/12-server-search.md` holds the search design.

What Fynd takes, for the free text search bar of release 2.

- The model classifies and the code decides. For each filter the app knows, it asks the model one closed question. The four answers are wanted, implied, avoided and not mentioned, and each carries a probability. Their note says it plainly: the model never produces a value.
- Confident answers become hard filters and weak answers only move the ranking. Their cut is 0.9 for a filter.
- Numbers are found by code, and the model only labels what each number means.
- A plain fallback with no model. When the model fails, search still works.
- The free text is bounded and escaped before it reaches a query. They trim to 300 characters, drop control characters, and they tested an injection attempt.

This is the opposite of one thing stage 2 does today. The model writes the Topic `query` string by hand and nothing tests it, which is the imprecise-search finding of day 8.

## APIs

| API | Link | Key needed | Used for |
|---|---|---|---|
| Semantic Scholar graph | https://api.semanticscholar.org/graph/v1/paper/search | Yes | The Paper search of stage 2 |
| OpenAlex works | https://api.openalex.org/works | No, a mailto is polite | Open copy resolution, and the stage 2 gate |
| OpenAlex fields | https://api.openalex.org/fields | No | The 26 candidate Domains of release 2 |
| OpenAlex topics | https://api.openalex.org/topics | No | A measurement of generator quality |

OpenAlex holds a taxonomy of four levels, which are domain, field, subfield and topic. Its 26 fields are the candidate Domain list of release 2. Energy is `https://openalex.org/fields/21`. A grouped request prices many topics at once, as in `?filter=topics.field.id:fields/21,is_oa:true,from_publication_date:2022-01-01&group_by=topics.id`.

# Database design for stage 1 to stage 3

Updated: 2026-10-06. Postgres on Supabase, with pgvector for stage 5.
Read [CONTEXT.md](../CONTEXT.md) for the words and [PRD.md](../PRD.md) for the scope.

This document covers stage 1 to stage 3, which is the immediate next task in [NEXT-STEPS.md](../NEXT-STEPS.md). Stage 4 to stage 7 add tables later, and this document names them at the end without defining them.

## The rule for a table against a JSON value

Stage state holds a JSON value. A list inside that JSON value is easy to write and hard to query. One rule decides where a thing goes.

A thing gets its own table when something else points at it, or when you filter, join, or index it. A thing stays in the JSON value when Fynd writes it once and only shows it.

By that rule the proposed Topic list stays in the stage 2 JSON value, because nothing points at a Topic. A candidate Problem gets a table, because a Claim points at it.

## Naming and type rules this design follows

- Every identifier is lower case with underscores. See the Postgres wiki page "Don't Do This".
- Every text column is `text`. A length limit goes in a check constraint, not in the type.
- Every time column is `timestamptz`. No column uses `timestamp`.
- Every primary key is `bigint generated always as identity`. No column uses `serial`.
- Every foreign key column has an index, because Postgres does not create one for you.
- A foreign key column is named after the table it points at, for example `project_id`.
- No column holds a null that means "not known yet". A missing row says that instead.

## The tables

### project

One row for one Project.

```sql
create table project (
  id bigint generated always as identity primary key,
  secret_link_id uuid not null default gen_random_uuid() unique,
  domain text not null,
  created_at timestamptz not null default now(),
  constraint project_domain_valid
    check (domain in ('technology', 'healthcare', 'energy'))
);
```

The `secret_link_id` is the value in the secret link. The `id` is what every other table points at. Two columns, not one, for two reasons. A leaked log line that holds a foreign key does not hand over a Project. You can also issue a new `secret_link_id` without moving a single row.

### stage_state

One row for one Stage of one Project.

```sql
create table stage_state (
  project_id bigint not null references project (id) on delete cascade,
  stage_number smallint not null,
  payload jsonb not null,
  completed_at timestamptz not null default now(),
  primary key (project_id, stage_number),
  constraint stage_state_stage_number_valid
    check (stage_number between 1 and 7)
);
```

The primary key is the pair, so one Stage of one Project cannot save twice. A Stage writes this row once, at the end of the Stage. A restart in the middle of a Stage runs the Stage again from the start.

No index on `project_id` is needed here, because `project_id` is the first column of the primary key.

The `stage_number` column is the number of the Stage, 1 to 7, in the order the PRD lists them. One Project that reached stage 3 holds three rows.

| project_id | stage_number | payload | completed_at |
|---|---|---|---|
| 12 | 1 | `{"domain": "energy"}` | 2026-10-06 09:14 |
| 12 | 2 | `{"picked": {"label": "...", "query": "..."}, "open_paper_count": 9}` | 2026-10-06 09:16 |
| 12 | 3 | `{"candidate_problem_id": 41, "round": 1}` | 2026-10-06 09:21 |

A number is enough because the Stages are a fixed sequence of seven. A name column adds a second thing to keep correct, and the number already sorts in the order the student walks.

### source

One row for one Source. A Source is a Paper, a Statistic, or a Product.

```sql
create table source (
  id bigint generated always as identity primary key,
  source_type text not null,
  title text not null,
  url text not null,
  external_id text not null default '',
  open_copy_url text not null default '',
  retrieved_at timestamptz not null default now(),
  constraint source_type_valid
    check (source_type in ('paper', 'statistic', 'product'))
);

create unique index source_external_id_key
  on source (external_id) where external_id <> '';
```

A Source is shared across Projects, because the same Paper serves many students and the disk cache already treats it as shared. The `external_id` holds the Semantic Scholar identifier for a Paper. The partial unique index stops the same Paper from arriving twice, and it lets a Statistic or a Product carry no identifier.

An empty string, not a null, marks "this Source has no open copy". That keeps the checks simple and matches the rule above.

### candidate_problem

One row for one candidate Problem at stage 3.

```sql
create table candidate_problem (
  id bigint generated always as identity primary key,
  project_id bigint not null references project (id) on delete cascade,
  statement text not null,
  place text not null,
  people_group text not null,
  round smallint not null default 1,
  is_picked boolean not null default false,
  created_at timestamptz not null default now(),
  constraint candidate_problem_place_present check (length(place) > 0),
  constraint candidate_problem_group_present check (length(people_group) > 0),
  constraint candidate_problem_round_valid check (round in (1, 2))
);

create index candidate_problem_project_id_idx on candidate_problem (project_id);

create unique index candidate_problem_one_pick
  on candidate_problem (project_id) where is_picked;
```

The two length checks are the specificity gate from stage 3. A candidate Problem with no place or no group of people never reaches the database.

The `round` column holds the one re-roll. The partial unique index allows one picked candidate Problem for each Project, which the database enforces instead of your code.

### claim

One row for one Claim. A Claim is one sentence from one Source, kept with its citation.

```sql
create table claim (
  id bigint generated always as identity primary key,
  source_id bigint not null references source (id) on delete restrict,
  quote text not null,
  located_at integer not null,
  created_at timestamptz not null default now(),
  constraint claim_quote_present check (length(quote) > 0),
  constraint claim_located check (located_at >= 0)
);

create index claim_source_id_idx on claim (source_id);
```

The `located_at` column holds the character position where the citation guard found the quote in the Source text. A row exists only after the guard passes, so a stored Claim is a verified Claim. This is why the guard cannot be softened later: the table has no place to put an unverified quote.

### candidate_problem_claim

The link between a candidate Problem and its Claims.

```sql
create table candidate_problem_claim (
  candidate_problem_id bigint not null
    references candidate_problem (id) on delete cascade,
  claim_id bigint not null references claim (id) on delete cascade,
  primary key (candidate_problem_id, claim_id)
);

create index candidate_problem_claim_claim_id_idx
  on candidate_problem_claim (claim_id);
```

A Claim can support more than one candidate Problem, and a candidate Problem holds 2 Claims. A link table carries that shape. Stage 5 adds its own link table from a Claim to an Existing approach, and the Claim rows stay where they are.

## What the JSON payload holds for each Stage

| Stage | Payload |
|---|---|
| 1 | The picked Domain. |
| 2 | The proposed Topic list, each with a label and a query. The picked Topic. The open Paper count from the check. |
| 3 | The identifier of the picked candidate Problem, and the round the student picked in. |

### How the payload is used

Three pieces of code touch the payload, and nothing else does.

1. A Stage finishes and writes one row. The write is the last step of the Stage, and it holds what the Stage decided.
2. A resume reads the highest `stage_number` for the Project. That number says which Stage runs next, and the payload says what the earlier Stages decided.
3. The page polls for progress and reads the same row count, so the student sees which Stage is done.

Fynd never filters or sorts on a value inside the payload. That is the reason a JSON value is safe here: a JSON value is slow to search and fine to read whole.

The payload repeats what the columns already hold for stage 1 and stage 3. That repeat is the point, because a resume must not depend on seven different joins being correct. One row answers what the Stage decided, and the tables answer everything the later Stages need to work with.

If you later need to filter on a payload value, that value has outgrown the payload and it belongs in a column.

## Row Level Security

Row Level Security is a Postgres switch that hides rows from a caller unless a policy allows them.

Fynd has no accounts, so the obvious reading is that there is nothing to protect per user, and that reading is correct. Row Level Security here does a different job. Supabase serves every table in the `public` schema over HTTP, and the anon key that reaches it is a public value by design. Row Level Security is the switch that makes that public door useless.

Turn it on, and write no policy. The result is that the `anon` role and the `authenticated` role read nothing and write nothing. FastAPI holds the service role key, and that key passes Row Level Security, so your own code is unaffected. The cost is one line for each table and no runtime cost, because a table with no policy needs no policy evaluation.

Skipping it is the real risk. A table in the `public` schema with Row Level Security off is readable and writable by anyone who has the anon key, and that key ships to the browser in a normal Supabase project. The secret link protects a Project inside FastAPI, and it protects nothing at the database door.

```sql
alter table project enable row level security;
alter table stage_state enable row level security;
alter table source enable row level security;
alter table candidate_problem enable row level security;
alter table claim enable row level security;
alter table candidate_problem_claim enable row level security;
```

FastAPI checks the secret link itself, by a lookup on `project.secret_link_id`. That check is authorization for a Project. Row Level Security is the lock on the door the student never uses.

## Tables that later Stages add

- `chunk`, for a piece of a Source with its embedding. Stage 5 needs pgvector and an index on that column.
- `existing_approach`, and a link table from a Claim to it.
- `gap`, with the Claims that support it.
- `proposal`, with the Technical core, the Point of difference, and the Source it cites.
- `export`, with the handover and its created time.
- `invite`, if a signed code needs a record of use.

## Open decisions

1. Whether a Source stays shared across Projects once two Domains are live.
2. The embedding model and the vector size for `chunk`. Stage 5 needs this before day 7.
3. Whether `invite` needs a table at all, because a signed code needs no storage to be checked.

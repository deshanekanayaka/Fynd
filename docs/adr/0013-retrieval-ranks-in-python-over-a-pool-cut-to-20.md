---
status: accepted
date: 2026-10-20
---

# Retrieval ranks in Python, over a pool cut to 20

Fynd searches for 50 Papers, ranks them in Python, and passes the top 20 to the Open copy pipeline and to stage 3. The keyword half of the ranking is BM25 in Python and not Postgres `tsvector`. pgvector stays, and it serves the stage 5 chunk search alone.

This supersedes the Retrieval row and the Storage row of the technical direction table in [PRD.md](../../PRD.md), which named hybrid search over Postgres `tsvector` and pgvector for Paper ranking.

## The two findings behind it

Postgres holds no BM25. Its full text search ranks with `ts_rank`, which weights a term differently, so a published BM25 number never describes a `tsvector` query. The two honest paths were a `ts_rank` row that nobody can compare against the literature, or BM25 in Python. One of the two is also the code that serves a student.

A Topic's pool is tens of Papers and not millions. The expensive work per Paper is the OpenAlex lookup, the robots.txt read and up to 3 fetch attempts, and none of that is ranking. Ranking 50 rows in memory costs nothing at serve time, and it needs no round trip to the database.

## Why the pool is cut to 20

The old flow searched for 20 Papers and kept all 20, so recall at 20 asked which 20 of 20 ranked first. The metric had no consequence, and `PRD.md` holds that a part with no number is a prompt. A metric with no consequence is the same hole.

One search call for 50 Papers costs the same one request as a call for 20. The cut then decides which 20 Papers a Project is built on, which is what recall at 20 measures.

The stage 2 gate counts the Papers with a candidate inside the top 20, and not inside the 50. The threshold stays at 3, so the promise to the student does not change.

## Consequences

`tsvector` leaves the Retrieval row and the Storage row of the technical direction table. The database skill those rows claimed now rests on the stage 5 chunk search, which has a row count that needs a database.

`src/fynd/retrieval.py` holds BM25, the dense ranking and the fusion. The measurement command and the Stage call the same functions, so the published number comes from the code that runs for a student.

The measurement harness needs no database and no network, which keeps the rule that no test reaches the network. It is still not a continuous integration gate, because it reads abstracts that git does not hold. See [ADR 0011](./0011-the-public-repository-holds-the-text-and-not-the-files.md).

A second measurement of the same number after a port to Postgres is no longer owed, because there is no port.

## Considered options

Rank with `tsvector` and `ts_rank` in Postgres. Rejected because `ts_rank` is not BM25, so the published table would describe code that never runs, and the number would not compare with any published retrieval result.

Keep the search at 20 Papers and rank them for the card order alone. Rejected because recall at 20 then measures nothing that changes a Project.

Search for 100 Papers, which is the Semantic Scholar maximum. Deferred. 50 is twice the cut, which is enough for the ranking to have work to do, and a larger pool costs more hand grading for the Retrieval set with no new decision behind it.

Pool four queries at serve time, as the Retrieval set does. Rejected for version 1. Four queries give about 80 Papers, and the fetch cost of the Open copy pipeline has no measured elapsed time yet.

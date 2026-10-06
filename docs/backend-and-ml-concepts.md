# Backend and machine learning concepts to know

Updated: 2026-10-06. For Deshan.
[docs/stages-and-prerequisites.md](./stages-and-prerequisites.md) says which Stage needs each subject. This document says what each concept is.

Each entry has a short meaning and the place Fynd uses it. Read an entry when you reach the work that needs it. Nothing here is a reading list to finish first.

## Backend: the Python and API layer

**HTTP**: the request and response protocol the web runs on. You need the methods, the status codes, and a JSON body. Fynd uses it for its own API and for every external fetch.

**REST**: an API style where a path names a thing and the method names the action. Fynd exposes one path for a Project and one for each Stage.

**FastAPI route**: a Python function that answers one path and one method. Fynd has one route for each Stage action.

**Pydantic model**: a class that states the shape of data and rejects data that does not match. Fynd uses it for request bodies, for responses, and for the JSON the model returns.

**Type hints**: the types you write in the function signature. They document the code and let a checker find a bug before the code runs. `AGENTS.md` requires them.

**async and await**: a way to wait for a network call without blocking the process. Stage 4 waits on many fetches, so the difference matters there.

**Dependency injection**: FastAPI passes a shared thing, for example a database connection, into a route for you. It keeps the connection setup out of every route.

**Environment variable**: a value the process reads from its environment instead of from the code. Every key and every connection string lives there, never in a file you commit.

**pytest**: the test runner. You need a plain test function, a fixture for shared setup, and `parametrize` for the same test over several inputs.

**Recorded response**: a saved copy of a real API reply, replayed in a test. It makes a test fast and repeatable, and it is the same idea as the disk cache.

**ruff**: the linter and formatter. It runs in continuous integration and it ends every style argument with yourself.

**Idempotent**: safe to run twice with the same result. A Stage that re-runs after a restart must be idempotent, which is why a Stage writes its state once at the end.

**Transaction**: a group of writes that all succeed or all fail. The Claims for one candidate Problem are written in one transaction.

**Migration**: a file that changes the database schema, kept in order and committed. The tables in [docs/database-design.md](./database-design.md) ship as migrations.

**Index**: a structure that makes a lookup fast. Postgres does not index a foreign key column for you, so you write those yourself.

**Connection pool**: a set of open database connections the app reuses. A free container with few connections needs the Supabase pooler, not a new connection for each request.

**Background task**: work that keeps running after the response is sent. The PRD puts the job inside the FastAPI process, because no free tier runs a separate worker.

**Polling**: the page asks "is it done yet" on a timer. The PRD chooses polling and rules out streaming.

**Rate limit**: the cap an API sets on requests over time. Semantic Scholar allows 1 request per second with a key, so stage 4 waits between calls on purpose.

**Backoff and retry**: wait longer after each failure before trying again. A fetch that fails once often succeeds a second time, and a retry without a wait makes the problem worse.

**Timeout**: the limit on how long you wait for a reply. Every external call needs one, because a call with no timeout can hold a Stage open past the 3 minute metric.

**Cache key**: the string that names a cached item. For a search it is the query and the parameters, so the same search returns the same cached file.

**Docker image and container**: the image is the packaged app, and the container is a running copy of it. Render runs your container, and the free plan stops it after 15 minutes with no requests.

**Cold start**: the delay while a stopped container starts again. It is the reason Stage state is saved after every Stage.

**Health check**: a cheap route that says the app is alive. A scheduled ping to it keeps the Supabase project awake.

**HMAC signature**: a short code computed from a value and a secret key, which proves the value was issued by you. The Invite is a signed code, and the check is a signature check and not a database lookup.

**Constant time compare**: comparing two secrets in a way that does not leak how much matched. Use the library function, never `==`, when you compare a signature.

**Structured logging**: a log line that is a JSON object with fields, not a sentence. It lets you find every call for one Project later.

## Machine learning and artificial intelligence

**Large language model**: a model that predicts text and follows instructions. Fynd uses Claude Haiku 4.5 for volume and Claude Opus 5 for the Proposal.

**Token**: the unit a model reads and writes, roughly a word piece. Cost and limits are counted in tokens, and the PRD estimates 240,000 input tokens of extraction for one Project.

**Context window**: the total tokens one call can hold. It is the reason a long Paper is split before extraction.

**Temperature**: how much randomness the model uses. Extraction runs near zero, because you want the same Claim every time.

**System prompt and user prompt**: the system prompt sets the role and the rules, and the user prompt carries the task and the data. Keep the Source text in the user prompt.

**Few-shot example**: one or two worked examples inside the prompt. Two examples of a good Claim do more for quality than a longer instruction.

**Structured output**: the model returns JSON that matches a schema you define. Fynd uses it for Topics, for candidate Problems, and for Claims.

**Schema validation and repair**: you check the returned JSON against the schema, and ask again when it fails. A model that returns one bad field is normal, and a crash on it is not acceptable.

**Prompt injection**: text inside a fetched Source that tries to give the model new instructions. A Paper and a web page are data and never instructions, so you label them as data in the prompt and you never let them change the task.

**Hallucination**: a confident statement with nothing behind it. It is the main risk in Fynd, and metric 1 measures it.

**Grounding**: tying output to text that exists. The citation guard is the mechanical form of grounding, because it searches the Source text for the quote.

**Chunking**: cutting a long text into pieces that fit one call. You need a size, an overlap, and a rule that avoids cutting a sentence in half.

**Embedding**: a list of numbers that carries the meaning of a piece of text. Two pieces about the same thing sit close together.

**Dimension**: how many numbers one embedding holds. The number is fixed by the model you pick, and the `chunk` table column must match it.

**Cosine similarity**: a measure of the angle between two embeddings, used as a score for "about the same thing".

**Vector index**: the pgvector index that makes a similarity search fast. HNSW is the common choice, and it returns an approximate answer, which is fine here.

**Top k retrieval**: take the k nearest chunks for a query. k is a number you tune, and a larger k costs more tokens.

**Hybrid search**: combine vector similarity with keyword search. A rare term, for example a place name, is found by keyword and missed by embeddings.

**Retrieval augmented generation**: retrieve the text first, then put it in the prompt. People call it RAG, and stage 5 is a RAG pipeline.

**Clustering**: grouping items that sit close together. A Gap is the shortcoming several Existing approaches share, so grouping Claims by similarity is how the Gap is found.

**Threshold against k**: with clustering you either fix the number of groups or fix how close two items must be. A threshold suits Fynd, because the number of real shortcomings is not known in advance.

**Labelled set**: a frozen set of inputs with the correct answers written by hand. The PRD fixes 10 Sources with their true Claims.

**Precision and recall**: precision is the share of returned Claims that are correct, and recall is the share of true Claims that were found. Metric 1 asks for 90 percent recall with zero invented Claims.

**Regression test**: a test that fails when a change makes quality worse. The labelled set becomes one, and it runs in continuous integration.

**Baseline**: the simple method a new method must beat. Every Proposal needs an evaluation plan with one, and a Proposal with no baseline cannot be marked.

**Tracing**: a record of every model call with its inputs, outputs, tokens, and cost. Langfuse holds it, and it is how you report cost for one Project.

## The order that matches the plan

1. HTTP, REST, rate limits, backoff, timeouts, and the cache key. Days 1 to 3.
2. Chunking, embeddings, cosine similarity, pgvector, and top k retrieval. Days 1 to 3.
3. Structured output, schema validation, prompt injection, and the citation guard. Days 4 to 6.
4. Clustering and the threshold choice. Days 4 to 6.
5. Prompting for candidate Problems and for the Proposal. Days 7 to 8.
6. Labelled set, precision and recall, regression tests, and tracing. Days 9 to 11.
7. FastAPI routes, background tasks, transactions, migrations, pooling, Docker, and cold starts. Days 12 to 14.

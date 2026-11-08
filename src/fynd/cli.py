"""Runs Fynd's Stage, file-reading, and measurement commands from the terminal.

This file loads .env, parses arguments, constructs real clients, and calls
Stage rules or measurement helpers. It prints decisions, saves graded sets
and reports, and presents expected service errors. Stage rules live in their
own files; this CLI has no persisted Projects or Stage state."""

import argparse
import datetime as dt
import os
import pathlib
import sys
import textwrap

import anthropic
import httpx
from dotenv import load_dotenv

from fynd.claude import ModelRefused, ask_for_json
from fynd.contact import ContactEmailMissing, contact_email
from fynd.extract import extract_html, extract_pdf
from fynd.fetcher import Fetched, Fetcher, FetchFailed, looks_like_a_pdf
from fynd.grading import GradeRefused, apply_grades, grade_counts, ungraded, worksheet_rows
from fynd.measure import OPEN_COPY_STEM, RETRIEVAL_STEM, readme_with, report
from fynd.open_copy import read_open_copy
from fynd.openalex import OpenAlex, WorkNotRead
from fynd.retrieval import Embed, bm25_ranking
from fynd.retrieval_report import (
    Row,
    dense_rows,
    rows_from_searches,
    shared_papers,
)
from fynd.retrieval_report import report as retrieval_report
from fynd.retrieval_set import (
    RetrievalSet,
    SetTooSmall,
    build_set,
    papers_without_abstract,
    pool_papers,
)
from fynd.semantic_scholar import RateLimited, SemanticScholar, cached_abstracts
from fynd.source_text import reason_against_paper_text
from fynd.stages import stage1, stage2
from fynd.voyage import ATLAS_KEY_PREFIX, EMBEDDING_MODEL, ReplyIncomplete, Voyage
from fynd.voyage import KeyMissing as VoyageKeyMissing
from fynd.voyage import RateLimited as VoyageRateLimited


def search_with(client: SemanticScholar):
    """Adapts the search client to the function Stage 2 expects."""

    def search(query: str, year_from: int):
        """Searches Papers using the supplied client."""
        return client.search(query, year_from=year_from)

    return search


def embed_with(voyage: Voyage, dimensions: int) -> Embed:
    """Binds a vector size to the embedding function used by retrieval."""

    def embed(texts: list[str], input_type: str) -> list[list[float]]:
        """Embeds texts using the supplied client and chosen vector size."""
        return voyage.embed(texts, input_type=input_type, dimensions=dimensions)

    return embed


def run_stage_1(domain: str) -> None:
    """Offers Domains and prints the decision for a supplied Pick."""
    offered = stage1.offer_domains()
    print("Stage 1 offers:", ", ".join(offered))
    answer = stage1.accept_domain(domain, offered)
    print("Stage 1 decided:", answer)
    # A nonzero exit status lets scripts detect an unoffered Pick.
    if isinstance(answer, stage1.DomainNotOffered):
        raise SystemExit(1)


def run_stage_2(domain: str, pick: str, avoid: list[str]) -> None:
    # Fail before model work when the CLI’s required API key is missing.
    """Offers Topics and optionally checks a supplied Topic slug."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "Set ANTHROPIC_API_KEY in your .env file. Stage 2 asks a model for Topics."
        )
    # Check the operator address before model work because the later gate needs OpenAlex.
    contact_email()

    offered = stage2.offer_topics(domain, ask_for_json, avoid=avoid or None)
    print(f"Stage 2 offers {len(offered)} Topics for the Domain {domain}.")
    for topic in offered:
        # Show the actual search words alongside the display label for inspection.
        print(f"  {topic.slug:40} {topic.label:45} {topic.query}")

    if not pick:
        print("\nPass --pick with one slug above to see the Open copy count.")
        return

    print()
    client = SemanticScholar()
    # Stage 2 owns the threshold; supply the real search and DOI lookup functions.
    answer = stage2.accept_topic(
        pick,
        offered,
        search_with(client),
        OpenAlex().resolve,
        today=dt.date.today(),
    )
    print("Stage 2 decided:", answer)
    if isinstance(answer, stage2.TopicNotOffered):
        raise SystemExit(1)


def run_resolve_open_copy(doi: str) -> None:
    """Prints the ordered file candidates for a DOI."""
    answer = OpenAlex().resolve(doi)
    if not answer.found:
        print(f"OpenAlex holds no record for {doi}.")
        raise SystemExit(1)
    if not answer.candidates:
        print(f"OpenAlex holds {doi}, and no file Fynd can fetch: {answer.reason}")
        raise SystemExit(1)

    # Show repository-first order so the output matches the download pipeline.
    print(f"{len(answer.candidates)} candidates for {doi}, in the order Fynd tries them.")
    for number, copy in enumerate(answer.candidates, start=1):
        print(f"{number} url     {copy.url}")
        print(f"  host    {copy.host}")
        print(f"  license {copy.license or 'not stated'}")


def run_fetch_open_copy(url: str) -> None:
    """Downloads one candidate URL and prints its byte count or refusal."""
    answer = Fetcher().fetch(url)
    if isinstance(answer, Fetched):
        print(f"bytes        {len(answer.data)}")
        print(f"content type {answer.content_type}")
        return
    print(f"refused      {answer.reason}")
    print(f"status       {answer.status or 'none'}")
    print(f"content type {answer.content_type or 'not stated'}")
    raise SystemExit(1)


def run_extract(path: str) -> None:
    """Extracts a local PDF or HTML file and prints its text preview."""
    data = pathlib.Path(path).read_bytes()
    # Choose the reader from file bytes, not a possibly misleading filename extension.
    if looks_like_a_pdf("", data):
        answer = extract_pdf(data)
    else:
        answer = extract_html(data)
    print(f"extractor  {answer.extractor}")
    print(f"characters {len(answer.text)}")
    for span in answer.structure:
        print(f"{span.kind} {span.label}: {span.start} to {span.end}")
    print()
    print(answer.text[:500])


# Keep generated reports under the repository’s measurement directory.
MEASUREMENT_DIR = pathlib.Path("docs/measurements")
# Save permitted graded metadata with the repository’s replay fixtures (ADR 0011).
RETRIEVAL_SET_DIR = pathlib.Path("tests/files")
GRADING_RULE = pathlib.Path("docs/retrieval-set-grading-rule.md")
MEASUREMENT_README = MEASUREMENT_DIR / "README.md"

# Request 20 Papers for this separate Open copy measurement command.
MEASURED_POOL_SIZE = 20


def run_measure_open_copies() -> None:
    """Runs the Seeded Topic file pipeline and saves its dated measurement report."""
    if not os.environ.get("SEMANTIC_SCHOLAR_API_KEY"):
        raise SystemExit(
            "Set SEMANTIC_SCHOLAR_API_KEY in your .env file. The measurement searches "
            "for the Seeded Topic before it fetches anything."
        )

    year_from = stage2.first_year_in_window(dt.date.today())
    search = SemanticScholar()
    found = search.search(stage2.SEEDED_TOPIC, year_from=year_from, limit=MEASURED_POOL_SIZE)
    print(f"{len(found.papers)} Papers for the Seeded Topic, from {year_from} onward.")

    resolver = OpenAlex()
    fetcher = Fetcher()
    results = []
    dropped: list = []
    for number, paper in enumerate(found.papers, start=1):
        # Process sequentially; the fetcher handles host delays and retries.
        try:
            result = read_open_copy(
                paper, resolver.resolve, fetcher.fetch, extract_pdf, reason_against_paper_text
            )
        except (WorkNotRead, FetchFailed) as error:
            # Keep interrupted Papers in the denominator even though they have no retained result.
            print(f"{number:3} {paper.title[:50]:50} failed: {error}")
            dropped.append(paper)
            continue
        results.append(result)
        host = result.open_copy.host if result.open_copy else "-"
        print(
            f"{number:3} {paper.title[:50]:50} {host:28} {result.attempts} tries  {result.reason}"
        )

    today = dt.date.today()
    measurement_file = MEASUREMENT_DIR / f"{OPEN_COPY_STEM}-{today.isoformat()}.md"
    MEASUREMENT_DIR.mkdir(parents=True, exist_ok=True)
    measurement_file.write_text(
        report(
            results,
            query=stage2.SEEDED_TOPIC,
            year_from=year_from,
            limit=MEASURED_POOL_SIZE,
            dropped=len(dropped),
            today=today,
        ),
        encoding="utf-8",
    )
    print(f"\nWrote {measurement_file}")

    existing_readme = ""
    if MEASUREMENT_README.exists():
        existing_readme = MEASUREMENT_README.read_text(encoding="utf-8")
    MEASUREMENT_README.write_text(
        readme_with(existing_readme, today, OPEN_COPY_STEM), encoding="utf-8"
    )
    print(f"Wrote {MEASUREMENT_README}")


def run_build_retrieval_set(as_of: str) -> None:
    """Builds and saves an ungraded Retrieval set for the supplied reference date."""
    if not os.environ.get("SEMANTIC_SCHOLAR_API_KEY"):
        raise SystemExit(
            "Set SEMANTIC_SCHOLAR_API_KEY in your .env file. The Retrieval set runs "
            "four searches for the Seeded Topic."
        )
    try:
        reference_date = dt.date.fromisoformat(as_of)
    except ValueError:
        raise SystemExit(
            f"--as-of needs a date like 2026-10-20, and it got {as_of!r}. Every "
            "published number states the date its Evidence window came from."
        ) from None

    client = SemanticScholar()
    built = build_set(client.search, reference_date=reference_date)

    for query in built.queries:
        found = [entry for entry in built.entries if query.name in entry.queries]
        print(f"{query.name:9} {len(found):3} Papers in the set  {query.text}")
    print(f"\n{len(built.entries)} Papers to grade, in a shuffled order.")
    if built.papers_offered > len(built.entries):
        left_out = built.papers_offered - len(built.entries)
        print(
            f"The four queries offered {built.papers_offered} Papers, so the cap left "
            f"{left_out} out. The set is a pool, and the table states that as a limit."
        )

    RETRIEVAL_SET_DIR.mkdir(parents=True, exist_ok=True)
    set_file = RETRIEVAL_SET_DIR / f"retrieval-set-{reference_date.isoformat()}.json"
    # Saved set metadata excludes abstracts; ranking reads them from the local search cache.
    set_file.write_text(built.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {set_file}")
    print(f"Grade it against {GRADING_RULE}. Every grade is 0, 1 or 2.")


def retrieval_set_path(as_of: str) -> pathlib.Path:
    """Returns the dated Retrieval set path under tests/files."""
    return RETRIEVAL_SET_DIR / f"retrieval-set-{as_of}.json"


def run_grade_retrieval_set(as_of: str, show: bool) -> None:
    """Shows saved grades or collects and saves new grades interactively."""
    set_file = retrieval_set_path(as_of)
    if not set_file.exists():
        raise SystemExit(
            f"No set file at {set_file}. Run build-retrieval-set --as-of {as_of} first."
        )
    held = RetrievalSet.model_validate_json(set_file.read_text(encoding="utf-8"))

    if show:
        for row in worksheet_rows(held):
            print(row)
        print()
        print(f"Counts: {grade_counts(held)}")
        return

    waiting = ungraded(held)
    if not waiting:
        print(f"Every Paper is graded. Counts: {grade_counts(held)}")
        return

    # Grading needs abstracts, but ADR 0011 keeps those cached texts out of git.
    abstracts = cached_abstracts()
    missing = [entry for entry in waiting if entry.paper_id not in abstracts]

    print(f"{len(waiting)} Papers to grade, for the Topic {held.topic}.")
    print("2 is on the subject. 1 covers part of it. 0 is another subject.")
    print(f"The full rule is {GRADING_RULE}. Press s to skip a Paper, or q to stop.")
    if missing:
        print(
            f"{len(missing)} of these Papers have no abstract anywhere in the cache, "
            "so they are graded on the title alone and the file says so."
        )
    print()

    for number, entry in enumerate(waiting, start=1):
        print(f"{number} of {len(waiting)}  {entry.title}")
        abstract = abstracts.get(entry.paper_id)
        if abstract:
            for line in textwrap.wrap(abstract, width=96):
                print(f"    {line}")
        else:
            print("    No abstract in the cache. Grade the title alone.")
        answer = input("  grade: ").strip().lower()
        if answer == "q":
            break
        if answer in ("s", ""):
            continue
        try:
            held = apply_grades(held, {entry.paper_id: int(answer)})
        except ValueError:
            print(f"  {answer!r} is not 0, 1 or 2. The Paper stays ungraded.")
            continue
        # Save each accepted grade so a later stop does not lose earlier answers.
        set_file.write_text(held.model_dump_json(indent=2) + "\n", encoding="utf-8")

    print(f"\nWrote {set_file}")
    print(f"Counts: {grade_counts(held)}")


class PoolChanged(Exception):
    """Raised when returned Paper identifiers differ from the graded pool."""


def run_measure_retrieval(as_of: str) -> None:
    """Measures saved human grades against ranking rows and writes the report."""
    if not os.environ.get("SEMANTIC_SCHOLAR_API_KEY"):
        raise SystemExit(
            "Set SEMANTIC_SCHOLAR_API_KEY in your .env file. The table rebuilds the "
            "order the four searches arrived in, and a cached reply still needs the key "
            "when one query is missing from the cache."
        )
    # Validate the configured Atlas key before searches and ranking work begin.
    if not os.environ.get("VOYAGE_API_KEY", "").startswith(ATLAS_KEY_PREFIX):
        raise SystemExit(
            "Set VOYAGE_API_KEY in your .env file to a key made in MongoDB Atlas, which "
            f"begins with {ATLAS_KEY_PREFIX!r}. The meaning rows embed every abstract in "
            "the pool, and the host this client asks accepts an Atlas key alone."
        )
    try:
        reference_date = dt.date.fromisoformat(as_of)
    except ValueError:
        raise SystemExit(
            f"--as-of needs a date like 2026-10-20, and it got {as_of!r}. Every "
            "published number states the date its Evidence window came from."
        ) from None

    set_file = retrieval_set_path(as_of)
    if not set_file.exists():
        raise SystemExit(
            f"No set file at {set_file}. Run build-retrieval-set --as-of {as_of} first."
        )
    held = RetrievalSet.model_validate_json(set_file.read_text(encoding="utf-8"))

    if not held.entries:
        raise SystemExit(
            f"The set at {set_file} holds no Papers. A table over an empty pool prints a "
            "dash in every cell and says nothing, so nothing is published for it."
        )

    ungraded_papers = ungraded(held)
    if ungraded_papers:
        raise SystemExit(
            f"{len(ungraded_papers)} Papers of {len(held.entries)} still carry no grade. "
            f"Run grade-retrieval-set --as-of {as_of} first, because a recall number over "
            "a half graded pool counts an ungraded Paper as a Paper nobody wants."
        )

    # Recover search order from matching replies because saved set entries are shuffled.
    year_from = stage2.first_year_in_window(reference_date)
    client = SemanticScholar()
    results = []
    for query in held.queries:
        # Use the saved limit so a changed default cannot select a different search cache entry.
        found = client.search(query.text, year_from=year_from, limit=held.search_limit)
        print(f"{query.name:9} {len(found.papers):3} Papers returned  {query.text}")
        results.append((query.name, found))

    graded = {entry.paper_id: entry.grade for entry in held.entries if entry.grade is not None}
    rows = rows_from_searches(results, per_query=held.per_query, pool_size=len(held.entries))
    reached = {paper_id for row in rows for paper_id in row.ranking}
    if reached != set(graded):
        # Refuse different identifiers instead of measuring Papers nobody graded.
        raise PoolChanged(
            f"The searches reached {len(reached)} of the {len(graded)} graded Papers. "
            "The cached replies of the day the set was built are gone, so the table "
            "would report a pool nobody graded. Restore the cache, or build and grade "
            "a new set."
        )

    # Reconstruct only the graded pool, including abstracts available in the search replies.
    pool = pool_papers(results, per_query=held.per_query, keep=set(graded))
    if not held.topic_query:
        raise SystemExit(
            f"The set at {set_file} records no `topic_query`. A ranking asks the pool "
            "for words, and the label of a Topic names a place the grading rule ignores. "
            "Add the subject words as `topic_query` to the file. See ADR 0015."
        )

    # Publish label and subject-query rows so the comparison does not hide the worse result.
    for asked, what in ((held.topic, "label"), (held.topic_query, "query")):
        rows.append(
            Row(
                name=f"BM25, {what}",
                note=f"BM25 over the pool, asked for the {what} `{asked}`",
                ranking=[item.paper_id for item in bm25_ranking(asked, pool)],
                is_fynd_ranking=True,
                reads_text=True,
            )
        )

    # The Voyage cache reuses Paper vectors across label and subject-query rows at each size.
    voyage = Voyage()
    strings = [("label", held.topic), ("query", held.topic_query)]
    rows += dense_rows(strings, pool, lambda size: embed_with(voyage, size), EMBEDDING_MODEL)
    print(f"\nVoyage charged this run for {voyage.tokens_used} tokens")

    today = dt.date.today()
    text = retrieval_report(
        rows=rows,
        grades=graded,
        queries=[(query.name, query.text) for query in held.queries],
        reference_date=reference_date,
        today=today,
        set_file=pathlib.PurePosixPath(set_file.as_posix()),
        per_query=held.per_query,
        shared=shared_papers(results, per_query=held.per_query),
        without_abstract=papers_without_abstract(pool),
    )

    # Name the report after its graded set; rebuilding that measurement replaces the same file.
    MEASUREMENT_DIR.mkdir(parents=True, exist_ok=True)
    measurement_file = MEASUREMENT_DIR / f"{RETRIEVAL_STEM}-{reference_date.isoformat()}.md"
    measurement_file.write_text(text, encoding="utf-8")
    print(f"\nWrote {measurement_file}")

    existing_readme = ""
    if MEASUREMENT_README.exists():
        existing_readme = MEASUREMENT_README.read_text(encoding="utf-8")
    MEASUREMENT_README.write_text(
        readme_with(existing_readme, reference_date, RETRIEVAL_STEM), encoding="utf-8"
    )
    print(f"Wrote {MEASUREMENT_README}")


def main() -> None:
    # Load .env only at the command boundary, not when library modules are imported.
    """Loads environment settings, dispatches a command, and reports expected failures."""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Run Fynd's Stage, file-reading, and measurement commands."
    )
    stages = parser.add_subparsers(dest="stage", required=True)

    first = stages.add_parser("stage1", help="pick a Domain")
    first.add_argument("--domain", required=True, help="the Domain the student picks")

    second = stages.add_parser("stage2", help="pick a Topic")
    second.add_argument("--domain", required=True, help="the Domain from stage 1")
    second.add_argument("--pick", default="", help="the slug of the Topic the student picks")
    second.add_argument(
        "--avoid",
        default="",
        help="comma separated labels the student already saw, which is a Re-roll",
    )

    resolve = stages.add_parser(
        "resolve-open-copy", help="find the Open copy of one Paper with OpenAlex"
    )
    resolve.add_argument("--doi", required=True, help="the digital object identifier of the Paper")

    extract = stages.add_parser("extract", help="turn one file into a Source text")
    extract.add_argument("--path", required=True, help="the file on disk to read")

    stages.add_parser("measure-open-copies", help="run the pipeline and write the table")

    grade = stages.add_parser(
        "grade-retrieval-set", help="write a Relevance grade on each Paper of the Retrieval set"
    )
    grade.add_argument("--as-of", required=True, help="the reference date of the set file")
    grade.add_argument(
        "--show",
        action="store_true",
        help="print every Paper with its grade and stop, writing nothing",
    )

    retrieval_set = stages.add_parser(
        "build-retrieval-set", help="run the four queries and write the ungraded Retrieval set"
    )
    retrieval_set.add_argument(
        "--as-of",
        required=True,
        help="the reference date the Evidence window is counted from, as 2026-10-20",
    )

    retrieval_table = stages.add_parser(
        "measure-retrieval", help="write the retrieval table for a graded Retrieval set"
    )
    retrieval_table.add_argument(
        "--as-of",
        required=True,
        help="the reference date of the graded set, as 2026-10-20",
    )

    fetch = stages.add_parser("fetch-open-copy", help="fetch one Open copy and keep the bytes")
    fetch.add_argument("--url", required=True, help="the candidate file URL to fetch")

    args = parser.parse_args()

    try:
        if args.stage == "stage1":
            run_stage_1(args.domain)
        elif args.stage == "stage2":
            avoid = [label.strip() for label in args.avoid.split(",") if label.strip()]
            run_stage_2(args.domain, args.pick, avoid)
        elif args.stage == "resolve-open-copy":
            run_resolve_open_copy(args.doi)
        elif args.stage == "extract":
            run_extract(args.path)
        elif args.stage == "measure-open-copies":
            run_measure_open_copies()
        elif args.stage == "build-retrieval-set":
            run_build_retrieval_set(args.as_of)
        elif args.stage == "grade-retrieval-set":
            run_grade_retrieval_set(args.as_of, args.show)
        elif args.stage == "measure-retrieval":
            run_measure_retrieval(args.as_of)
        else:
            run_fetch_open_copy(args.url)
    except (
        RateLimited,
        ModelRefused,
        stage2.TopicListUnusable,
        WorkNotRead,
        FetchFailed,
        ContactEmailMissing,
        SetTooSmall,
        GradeRefused,
        PoolChanged,
        VoyageKeyMissing,
        VoyageRateLimited,
        ReplyIncomplete,
        anthropic.AnthropicError,
        # Present HTTP status and transport failures through the same concise CLI error path.
        httpx.HTTPError,
    ) as error:
        # Expected failures need an actionable message and nonzero exit status.
        print(error, file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

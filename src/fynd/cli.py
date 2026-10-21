"""Run a Stage from the command line.

An edge. It reads the environment, builds the real search and the real model,
and passes them to a Stage as plain arguments. Every rule lives in the Stage.

The runner and the database do not exist yet, so this command keeps no state
between runs. It offers the Topics again before it reads a Pick, which costs
nothing and returns the same list, because the cache holds it.
"""

import argparse
import datetime as dt
import os
import pathlib
import sys
import textwrap

import anthropic
from dotenv import load_dotenv

from fynd.claude import ModelRefused, ask_for_json
from fynd.contact import ContactEmailMissing, contact_email
from fynd.extract import extract_html, extract_pdf
from fynd.fetcher import Fetched, Fetcher, FetchFailed, looks_like_a_pdf
from fynd.grading import GradeRefused, apply_grades, grade_counts, ungraded, worksheet_rows
from fynd.measure import OPEN_COPY_STEM, RETRIEVAL_STEM, readme_with, report
from fynd.open_copy import read_open_copy
from fynd.openalex import OpenAlex, WorkNotRead
from fynd.retrieval import bm25_ranking
from fynd.retrieval_report import (
    Row,
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


def search_with(client: SemanticScholar):
    """Returns the search function stage 2 calls."""

    def search(query: str, year_from: int):
        return client.search(query, year_from=year_from)

    return search


def run_stage_1(domain: str) -> None:
    offered = stage1.offer_domains()
    print("Stage 1 offers:", ", ".join(offered))
    answer = stage1.accept_domain(domain, offered)
    print("Stage 1 decided:", answer)
    # A refused Domain leaves a non-zero exit code, so a script and a reader
    # both see the difference between a typo and an accepted Pick.
    if isinstance(answer, stage1.DomainNotOffered):
        raise SystemExit(1)


def run_stage_2(domain: str, pick: str, avoid: list[str]) -> None:
    # The most likely first run failure, so it gets a sentence and not a
    # traceback from inside the client.
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "Set ANTHROPIC_API_KEY in your .env file. Stage 2 asks a model for Topics."
        )
    # The gate asks OpenAlex, and every outbound request names a human. The
    # check runs first, so a missing address costs no model call and no search.
    contact_email()

    offered = stage2.offer_topics(domain, ask_for_json, avoid=avoid or None)
    print(f"Stage 2 offers {len(offered)} Topics for the Domain {domain}.")
    for topic in offered:
        # The query is printed beside the label, because it is the text that
        # reaches Semantic Scholar and the Retrieval set records it verbatim.
        print(f"  {topic.slug:40} {topic.label:45} {topic.query}")

    if not pick:
        print("\nPass --pick with one slug above to see the Open copy count.")
        return

    print()
    client = SemanticScholar()
    # The gate asks OpenAlex about each Paper of the search. A found record and
    # a plain no are both cached, so a second run of the same Topic asks again
    # only for the Papers whose lookup failed.
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
    answer = OpenAlex().resolve(doi)
    if not answer.found:
        print(f"OpenAlex holds no record for {doi}.")
        raise SystemExit(1)
    if not answer.candidates:
        print(f"OpenAlex holds {doi}, and no file Fynd can fetch: {answer.reason}")
        raise SystemExit(1)

    # Every candidate, in the order the pipeline would try them. A repository
    # ranks first and a journal second. See ADR 0012.
    print(f"{len(answer.candidates)} candidates for {doi}, in the order Fynd tries them.")
    for number, copy in enumerate(answer.candidates, start=1):
        print(f"{number} url     {copy.url}")
        print(f"  host    {copy.host}")
        print(f"  license {copy.license or 'not stated'}")


def run_fetch_open_copy(url: str) -> None:
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
    data = pathlib.Path(path).read_bytes()
    # The bytes decide, and not the file name. A page saved as a .pdf is a page.
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


# The Seeded Topic, fixed here so the published table names one query. The
# label and the query of a real stage 2 run come from a model, and a published
# number cannot depend on a model call.
MEASUREMENT_DIR = pathlib.Path("docs/measurements")
# The Retrieval set sits with the other committed test data, because the
# retrieval measurement replays it the way the pool file is replayed.
RETRIEVAL_SET_DIR = pathlib.Path("tests/files")
GRADING_RULE = pathlib.Path("docs/retrieval-set-grading-rule.md")
MEASUREMENT_README = MEASUREMENT_DIR / "README.md"

# The size of the measured pool. The table names it, so a reader knows the
# denominator even when a Paper drops out of the run.
MEASURED_POOL_SIZE = 20


def run_measure_open_copies() -> None:
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
        # One Paper at a time. The fetcher waits one second for each host, and
        # a refused host never stops the run.
        try:
            result = read_open_copy(
                paper, resolver.resolve, fetcher.fetch, extract_pdf, reason_against_paper_text
            )
        except (WorkNotRead, FetchFailed) as error:
            # A failure is not an answer, so nothing of it is cached. The Paper
            # is counted as dropped, because a table that loses a Paper in
            # silence under counts the pool and says nothing about it.
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
    # The abstracts are not written. The measurement reads them from the cache,
    # because ADR 0011 refuses a committed abstract and this file enters git.
    set_file.write_text(built.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {set_file}")
    print(f"Grade it against {GRADING_RULE}. Every grade is 0, 1 or 2.")


def retrieval_set_path(as_of: str) -> pathlib.Path:
    """Returns the set file for one reference date, the way the builder named it."""
    return RETRIEVAL_SET_DIR / f"retrieval-set-{as_of}.json"


def run_grade_retrieval_set(as_of: str, show: bool) -> None:
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

    # The abstract is read from the disk cache and never written anywhere. The
    # rule says to read the title and the abstract, and ADR 0011 keeps an
    # abstract out of git, so the two live together here.
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
        # Written after every answer, so a stopped session loses nothing.
        set_file.write_text(held.model_dump_json(indent=2) + "\n", encoding="utf-8")

    print(f"\nWrote {set_file}")
    print(f"Counts: {grade_counts(held)}")


class PoolChanged(Exception):
    """Raised when the searches no longer return the Papers that were graded."""


def run_measure_retrieval(as_of: str) -> None:
    """Writes the retrieval table for the graded set of one reference date."""
    if not os.environ.get("SEMANTIC_SCHOLAR_API_KEY"):
        raise SystemExit(
            "Set SEMANTIC_SCHOLAR_API_KEY in your .env file. The table rebuilds the "
            "order the four searches arrived in, and a cached reply still needs the key "
            "when one query is missing from the cache."
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

    # The set file holds the grades in a shuffled order and no rank, so the
    # order the searches arrived in is rebuilt from the cache. Every reply is
    # already on disk from the day the set was built.
    year_from = stage2.first_year_in_window(reference_date)
    client = SemanticScholar()
    results = []
    for query in held.queries:
        # The limit of the set file and not the constant of today. The limit is
        # part of the search cache key, so asking with another one misses the
        # cache, refetches live, and returns a pool nobody graded.
        found = client.search(query.text, year_from=year_from, limit=held.search_limit)
        print(f"{query.name:9} {len(found.papers):3} Papers returned  {query.text}")
        results.append((query.name, found))

    graded = {entry.paper_id: entry.grade for entry in held.entries if entry.grade is not None}
    rows = rows_from_searches(results, per_query=held.per_query, pool_size=len(held.entries))
    reached = {paper_id for row in rows for paper_id in row.ranking}
    if reached != set(graded):
        # A search that answers with other Papers today means the cache was
        # cleared and the pool moved. Every number would then be measured over
        # a pool that nobody graded.
        raise PoolChanged(
            f"The searches reached {len(reached)} of the {len(graded)} graded Papers. "
            "The cached replies of the day the set was built are gone, so the table "
            "would report a pool nobody graded. Restore the cache, or build and grade "
            "a new set."
        )

    # The Papers with their abstracts, which only a text ranking needs. The set
    # file holds no abstract, so the text comes from the search cache and is
    # written nowhere. See ADR 0011.
    pool = pool_papers(results, per_query=held.per_query, keep=set(graded))
    if not held.topic_query:
        raise SystemExit(
            f"The set at {set_file} records no `topic_query`. A ranking asks the pool "
            "for words, and the label of a Topic names a place the grading rule ignores. "
            "Add the subject words as `topic_query` to the file. See ADR 0015."
        )

    # Two BM25 rows and not one. The label names the place and the query names
    # the subject, and the gap between the two rows is the finding of day 12.
    # Both are published, because a table that showed only the better one would
    # be a configuration chosen after seeing the numbers. See ADR 0015.
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

    # The table is named after the graded set and not after today, because the
    # set decides every number in it. A second run of the same set rewrites the
    # same file, and a second set gets its own file instead of overwriting one.
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
    # Only the command line reads the .env file. A library that reads it would
    # change the environment under a test.
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run one Stage of Fynd.")
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
    fetch.add_argument("--url", required=True, help="the repository link OpenAlex resolved")

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
        anthropic.AnthropicError,
    ) as error:
        # A traceback teaches the reader nothing here. The message is the fix.
        print(error, file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

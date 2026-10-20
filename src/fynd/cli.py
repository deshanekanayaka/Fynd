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

import anthropic
from dotenv import load_dotenv

from fynd.claude import ModelRefused, ask_for_json
from fynd.contact import ContactEmailMissing, contact_email
from fynd.extract import extract_html, extract_pdf
from fynd.fetcher import Fetched, Fetcher, FetchFailed, looks_like_a_pdf
from fynd.measure import readme_with, report
from fynd.open_copy import read_open_copy
from fynd.openalex import OpenAlex, WorkNotRead
from fynd.retrieval_set import SetTooSmallOrTooBig, build_set
from fynd.semantic_scholar import RateLimited, SemanticScholar
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
        print(f"  {topic.slug:40} {topic.label}")

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
SEEDED_TOPIC_QUERY = "United Kingdom household energy forecasting"
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
    found = search.search(SEEDED_TOPIC_QUERY, year_from=year_from, limit=MEASURED_POOL_SIZE)
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
            f"{number:3} {paper.title[:50]:50} {host:28} "
            f"{result.attempts} tries  {result.reason}"
        )

    today = dt.date.today()
    measurement_file = MEASUREMENT_DIR / f"open-copy-hosts-{today.isoformat()}.md"
    MEASUREMENT_DIR.mkdir(parents=True, exist_ok=True)
    measurement_file.write_text(
        report(
            results,
            query=SEEDED_TOPIC_QUERY,
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
    MEASUREMENT_README.write_text(readme_with(existing_readme, today), encoding="utf-8")
    print(f"Wrote {MEASUREMENT_README}")


def run_build_retrieval_set(as_of: str, model_query: str) -> None:
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

    def search(query: str, year_from: int, limit: int):
        return client.search(query, year_from=year_from, limit=limit)

    built = build_set(search, reference_date=reference_date, model_query=model_query)

    for query in built.queries:
        found = [entry for entry in built.entries if query.name in entry.queries]
        print(f"{query.name:9} {len(found):3} Papers in the set  {query.text}")
    print(f"\n{len(built.entries)} Papers to grade, in a shuffled order.")

    RETRIEVAL_SET_DIR.mkdir(parents=True, exist_ok=True)
    set_file = RETRIEVAL_SET_DIR / f"retrieval-set-{reference_date.isoformat()}.json"
    # The abstracts are not written. The measurement reads them from the cache,
    # because ADR 0011 refuses a committed abstract and this file enters git.
    set_file.write_text(built.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {set_file}")
    print(f"Grade it against {GRADING_RULE}. Every grade is 0, 1 or 2.")


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

    retrieval_set = stages.add_parser(
        "build-retrieval-set", help="run the four queries and write the ungraded Retrieval set"
    )
    retrieval_set.add_argument(
        "--as-of",
        required=True,
        help="the reference date the Evidence window is counted from, as 2026-10-20",
    )
    retrieval_set.add_argument(
        "--model-query",
        required=True,
        help="the query the model wrote for the Seeded Topic, copied from a stage2 run",
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
            run_build_retrieval_set(args.as_of, args.model_query)
        else:
            run_fetch_open_copy(args.url)
    except (
        RateLimited,
        ModelRefused,
        stage2.TopicListUnusable,
        WorkNotRead,
        FetchFailed,
        ContactEmailMissing,
        SetTooSmallOrTooBig,
        anthropic.AnthropicError,
    ) as error:
        # A traceback teaches the reader nothing here. The message is the fix.
        print(error, file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

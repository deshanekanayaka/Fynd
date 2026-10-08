"""Run a Stage from the command line.

This file is an edge. It reads the environment, builds the real search and the
real model, and passes them to the Stage as plain arguments. Every rule lives
in the Stage file. See ADR 0006.

The runner and the database do not exist yet, so this command holds no state
between runs. It offers the Topics again before it reads a Pick, and the cache
makes that free and returns the same list, because temperature is zero.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import sys

import anthropic
from dotenv import load_dotenv

from fynd.claude import ModelRefused, ask_for_json
from fynd.semantic_scholar import RateLimited, SemanticScholar
from fynd.stages import stage1, stage2


def search_with(client: SemanticScholar):
    """Return the search function the Stage calls."""

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

    offered = stage2.offer_topics(domain, ask_for_json, avoid=avoid or None)
    print(f"Stage 2 offers {len(offered)} Topics for the Domain {domain}.")
    for topic in offered:
        print(f"  {topic.slug:40} {topic.label}")

    if not pick:
        print("\nPass --pick with one slug above to see the Open copy count.")
        return

    print()
    client = SemanticScholar()
    answer = stage2.accept_topic(
        pick,
        offered,
        search_with(client),
        today=dt.date.today(),
    )
    print("Stage 2 decided:", answer)
    if isinstance(answer, stage2.TopicNotOffered):
        raise SystemExit(1)


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

    args = parser.parse_args()

    try:
        if args.stage == "stage1":
            run_stage_1(args.domain)
        else:
            avoid = [label.strip() for label in args.avoid.split(",") if label.strip()]
            run_stage_2(args.domain, args.pick, avoid)
    except (
        RateLimited,
        ModelRefused,
        stage2.TopicListUnusable,
        anthropic.AnthropicError,
    ) as error:
        # A traceback teaches the reader nothing here. The message is the fix.
        print(error, file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

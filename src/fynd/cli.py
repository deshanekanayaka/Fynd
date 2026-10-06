"""Run one search from the command line.

Day 1 of the plan ends here: a command line run returns Papers for one Topic.
"""

from __future__ import annotations

import argparse
import sys

from dotenv import load_dotenv

from fynd.semantic_scholar import RateLimited, SemanticScholar

# The Seeded Topic from the PRD. It is the default so a run needs no argument.
SEEDED_TOPIC = "United Kingdom household energy forecasting"


def main() -> None:
    # Only the command line reads the .env file. A library that reads it would
    # change the environment under a test.
    load_dotenv()

    parser = argparse.ArgumentParser(description="Search Semantic Scholar for Papers.")
    parser.add_argument("--topic", default=SEEDED_TOPIC, help="the Topic to search for")
    parser.add_argument("--limit", type=int, default=20, help="how many Papers to ask for")
    args = parser.parse_args()

    try:
        result = SemanticScholar().search(args.topic, limit=args.limit)
    except RateLimited as error:
        # A traceback teaches the reader nothing here. The message is the fix.
        print(error, file=sys.stderr)
        raise SystemExit(1) from None

    print(f"Topic: {result.query}")
    print(f"Papers returned: {len(result.papers)} of {result.total} matches")
    print(f"Papers with an open copy: {result.open_copy_count}")
    print()
    for paper in result.papers:
        mark = "open" if paper.has_open_copy else "    "
        print(f"[{mark}] {paper.year or '????'}  {paper.title}")


if __name__ == "__main__":
    main()

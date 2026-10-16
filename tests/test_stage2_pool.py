"""The stage 2 gate, replayed over the committed pool of 2026-10-09.

The 20 Papers of the Seeded Topic run are in `tests/files/pool-2026-10-09.json`,
and the 20 OpenAlex answers for them are in `.cache`, which git holds. So the
old number and the new number both come from measured data here, and neither is
written into the test by hand.
"""

import json
from pathlib import Path
from typing import Any

import pytest

from fynd.models import Paper, SearchResult
from fynd.openalex import OpenAlex
from fynd.stages.stage2 import OPEN_PAPER_THRESHOLD, count_papers_with_a_candidate

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
POOL_FILE = REPOSITORY_ROOT / "tests" / "files" / "pool-2026-10-09.json"
COMMITTED_CACHE = REPOSITORY_ROOT / ".cache"


class ClientThatRefuses:
    """Stands in for the HTTP client, and fails the test if anything calls it."""

    def get(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("The replay reached the network, and every answer is in git.")


@pytest.fixture
def pool() -> SearchResult:
    """Returns the 20 Papers of the run of 2026-10-09, as the search returned them."""
    items = json.loads(POOL_FILE.read_text(encoding="utf-8"))
    papers = [Paper(**item) for item in items]
    query = "United Kingdom household energy forecasting"
    return SearchResult(query=query, total=20, papers=papers)


@pytest.fixture
def resolve(monkeypatch: pytest.MonkeyPatch):
    """Returns the OpenAlex lookup, reading the answers git holds."""
    monkeypatch.setenv("FYND_CACHE_DIR", str(COMMITTED_CACHE))
    return OpenAlex(client=ClientThatRefuses()).resolve  # type: ignore[arg-type]


def test_the_pool_holds_twenty_papers(pool: SearchResult) -> None:
    assert len(pool.papers) == 20


def test_semantic_scholar_claims_more_open_papers_than_hold_a_file(pool, resolve) -> None:
    # The field Semantic Scholar fills counts a Paper whose only address is a
    # doi.org lookup, which holds no file. The gate counts the files instead.
    assert pool.open_copy_count == 14
    assert count_papers_with_a_candidate(pool, resolve) == 10


def test_the_measured_pool_passes_the_threshold(pool, resolve) -> None:
    # 10 Papers against a threshold of 3. The Seeded Topic passes stage 2 on a
    # number the pipeline can try, and the stage 4 guard of 2 is the second net.
    assert count_papers_with_a_candidate(pool, resolve) >= OPEN_PAPER_THRESHOLD

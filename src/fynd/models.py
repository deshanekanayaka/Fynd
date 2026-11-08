"""Defines Topics, Papers, search responses, and Open copy locations.

Stage 2 creates Topics for the student to pick. The Semantic Scholar client
turns search replies into Papers and SearchResults for Stage 2 and retrieval.
The OpenAlex client returns OpenCopy locations for the file-fetching pipeline.

These shared types let that code use named fields instead of raw API replies.
Pydantic checks field types; Stage and fetching code enforce product rules.
"""

from pydantic import BaseModel, Field


class Topic(BaseModel):
    """One Topic a Stage offered."""

    # A Pick names the slug, so it does not depend on the display label.
    slug: str
    # Keep the place in the label and out of the search query (ADR 0015).
    label: str
    query: str


class Paper(BaseModel):
    """One published academic work, as Semantic Scholar returns it."""

    paper_id: str
    title: str
    abstract: str = ""
    year: int | None = None
    # OpenAlex uses the DOI to look up an Open copy.
    doi: str = ""
    open_copy_url: str = ""

    @property
    def has_open_copy(self) -> bool:
        """Reports whether Semantic Scholar supplied an open link."""
        # A reported link may be a landing page, so this does not verify a file.
        return bool(self.open_copy_url)


class SearchResult(BaseModel):
    """One page of Papers for one query."""

    query: str
    total: int = 0
    # Each search result needs its own list of Papers.
    papers: list[Paper] = Field(default_factory=list)

    @property
    def open_copy_count(self) -> int:
        """Counts Papers with an open link reported by Semantic Scholar."""
        # Stage 2 uses OpenAlex candidates instead; reported links can hold no file.
        count = 0
        for paper in self.papers:
            if paper.has_open_copy:
                count += 1
        return count


class OpenCopy(BaseModel):
    """The free file of a Paper, as OpenAlex located it."""

    url: str
    # Measurements group fetch outcomes by host.
    host: str
    license: str = ""

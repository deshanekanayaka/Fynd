"""The shapes Fynd passes between its own parts.

The words follow CONTEXT.md. These are pydantic models, not dataclasses,
because each one is built from an API reply that leaves fields out.
"""

from pydantic import BaseModel, Field


class Topic(BaseModel):
    """One Topic a Stage offered."""

    # The slug is what a Pick names, per ADR 0003. The label and the query both
    # come from the model, per ADR 0002, so no later Stage rewrites one into
    # the other.
    slug: str
    label: str
    query: str


class Paper(BaseModel):
    """One published academic work, as Semantic Scholar returns it."""

    paper_id: str
    title: str
    abstract: str = ""
    year: int | None = None
    # ADR 0007 added the digital object identifier, which OpenAlex needs to
    # resolve the Open copy, and dropped the arXiv identifier, because the
    # first live run returned none.
    doi: str = ""
    open_copy_url: str = ""

    @property
    def has_open_copy(self) -> bool:
        """Says whether this Paper has an Open copy link."""
        return bool(self.open_copy_url)


class SearchResult(BaseModel):
    """One page of Papers for one query."""

    query: str
    total: int = 0
    papers: list[Paper] = Field(default_factory=list)

    @property
    def open_copy_count(self) -> int:
        """Counts the Papers with an Open copy, which is what stage 2 reads."""
        # The search asks for the Evidence window, so every Paper counted here
        # is inside it. See ADR 0008.
        count = 0
        for paper in self.papers:
            if paper.has_open_copy:
                count += 1
        return count

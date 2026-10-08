"""The shapes Fynd passes between its own parts.

The words here follow CONTEXT.md. A Paper is one published academic work, and
a Paper is one kind of Source. A Topic is the narrow area a Project works in.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Topic(BaseModel):
    """One Topic a Stage offered.

    ADR 0002 gives a Topic two fields from the model, so no later Stage rewrites
    a label into a query. The slug is what a Pick names, per ADR 0003.
    """

    slug: str
    label: str
    query: str


class Paper(BaseModel):
    """One published academic work, as Semantic Scholar returns it."""

    paper_id: str
    title: str
    abstract: str = ""
    year: int | None = None
    # The digital object identifier is the key OpenAlex needs to resolve the
    # Open copy a second time. ADR 0007 added it, and dropped the arXiv
    # identifier, because the first live run returned none.
    doi: str = ""
    open_copy_url: str = ""

    @property
    def has_open_copy(self) -> bool:
        """Say whether an Open copy link exists, which is what stage 2 counts."""
        return bool(self.open_copy_url)


class SearchResult(BaseModel):
    """One page of Papers for one query."""

    query: str
    total: int = 0
    papers: list[Paper] = Field(default_factory=list)

    @property
    def open_copy_count(self) -> int:
        """Count the Papers with an Open copy.

        Stage 2 keeps a Topic only when this count reaches the threshold. The
        search already asks for Papers inside the Evidence window, so every
        Paper counted here is inside it. See ADR 0002 and ADR 0008.
        """
        count = 0
        for paper in self.papers:
            if paper.has_open_copy:
                count += 1
        return count

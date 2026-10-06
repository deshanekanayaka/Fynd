"""The shapes Fynd reads from an external API.

The words here follow CONTEXT.md. A Paper is one published academic work, and
a Paper is one kind of Source.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Paper(BaseModel):
    """One published academic work, as Semantic Scholar returns it."""

    paper_id: str
    title: str
    abstract: str = ""
    year: int | None = None
    arxiv_id: str = ""
    open_copy_url: str = ""
    # The field is on the model because stage 2 counts the Papers with an open
    # copy, and stage 4 only fetches full text for those.

    @property
    def has_open_copy(self) -> bool:
        """Say whether an open copy exists, which is what stage 2 counts."""
        return bool(self.open_copy_url)


class SearchResult(BaseModel):
    """One page of Papers for one query."""

    query: str
    total: int = 0
    papers: list[Paper] = Field(default_factory=list)

    @property
    def open_copy_count(self) -> int:
        """Count the Papers with an open copy.

        Stage 2 keeps a Topic only when this count reaches the threshold. See
        ADR 0002.
        """
        count = 0
        for paper in self.papers:
            if paper.has_open_copy:
                count += 1
        return count

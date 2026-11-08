"""Applies human Relevance grades to copies of the Retrieval set.

The CLI collects grades by Paper identifier, then uses these helpers to check
them, list ungraded Papers, and show counts. Unknown Papers, unsupported grades,
and conflicting overwrites are refused. The CLI handles saving the updated set.
"""

from fynd.retrieval_set import RetrievalSet, SetEntry

LEGAL_GRADES = (0, 1, 2)


class GradeRefused(Exception):
    """Raised for an unknown Paper, unsupported grade, or conflicting overwrite."""


def apply_grades(retrieval_set: RetrievalSet, grades: dict[str, int]) -> RetrievalSet:
    """Returns a copy with validated grades matched to Paper identifiers."""
    by_identifier = {entry.paper_id: entry for entry in retrieval_set.entries}

    # Validate the whole batch before applying any grade, so refusal cannot partly update it.
    for paper_id, grade in grades.items():
        entry = by_identifier.get(paper_id)
        if entry is None:
            raise GradeRefused(
                f"The set holds no Paper {paper_id}. A grade for a Paper that is not in "
                "the set cannot be applied. Check the identifier against this Retrieval set."
            )
        if grade not in LEGAL_GRADES:
            raise GradeRefused(
                f"The grade {grade} for Paper {paper_id} is not 0, 1 or 2. See "
                "docs/retrieval-set-grading-rule.md."
            )
        if entry.grade is not None and entry.grade != grade:
            # A disagreement must be resolved deliberately, not silently overwritten.
            raise GradeRefused(
                f"Paper {paper_id} already carries the grade {entry.grade}, and this pass "
                f"says {grade}. Clear the first grade by hand if the second one is right, "
                "so the change is a decision and not an accident."
            )

    # Copy nested entries too, so changing a grade cannot mutate the caller's set.
    written = retrieval_set.model_copy(deep=True)
    for entry in written.entries:
        if entry.paper_id in grades:
            entry.grade = grades[entry.paper_id]
    return written


def ungraded(retrieval_set: RetrievalSet) -> list[SetEntry]:
    """Returns entries whose Relevance grade is still None."""
    return [entry for entry in retrieval_set.entries if entry.grade is None]


def grade_counts(retrieval_set: RetrievalSet) -> dict[int | None, int]:
    """Counts present Relevance grades, including None for ungraded Papers."""
    counts: dict[int | None, int] = {}
    for entry in retrieval_set.entries:
        counts[entry.grade] = counts.get(entry.grade, 0) + 1
    return counts


def worksheet_rows(retrieval_set: RetrievalSet) -> list[str]:
    """Formats identifiers, titles, and grades in the saved entry order."""
    # Preserve the shuffled order instead of exposing query groups or ranking cues.
    rows = []
    for number, entry in enumerate(retrieval_set.entries, start=1):
        grade = "." if entry.grade is None else str(entry.grade)
        rows.append(f"{number:3} {grade}  {entry.paper_id:42} {entry.title}")
    return rows

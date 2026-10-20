"""Write the hand grades onto the Retrieval set, and say what is left.

Grading is the one step of this measurement that a person does. So this file
refuses anything it cannot be sure about. A grade names a Paper by identifier,
never by its place in a list, because a grade on the wrong Paper is invisible
to every number downstream.

It also refuses to replace a grade that is already there. A second pass over
the same Paper is a re-grade, and a re-grade that quietly overwrites the first
answer hides a disagreement worth seeing.
"""

from fynd.retrieval_set import RetrievalSet, SetEntry

LEGAL_GRADES = (0, 1, 2)


class GradeRefused(Exception):
    """Raised when a grade cannot be written without losing something."""


def apply_grades(retrieval_set: RetrievalSet, grades: dict[str, int]) -> RetrievalSet:
    """Returns the set with the grades written on, leaving the input alone."""
    by_identifier = {entry.paper_id: entry for entry in retrieval_set.entries}

    for paper_id, grade in grades.items():
        entry = by_identifier.get(paper_id)
        if entry is None:
            raise GradeRefused(
                f"The set holds no Paper {paper_id}. A grade for a Paper that is not in "
                "the set means the grades and the set came from different runs."
            )
        if grade not in LEGAL_GRADES:
            raise GradeRefused(
                f"The grade {grade} for Paper {paper_id} is not 0, 1 or 2. See "
                "docs/retrieval-set-grading-rule.md."
            )
        if entry.grade is not None and entry.grade != grade:
            raise GradeRefused(
                f"Paper {paper_id} already carries the grade {entry.grade}, and this pass "
                f"says {grade}. Clear the first grade by hand if the second one is right, "
                "so the change is a decision and not an accident."
            )

    written = retrieval_set.model_copy(deep=True)
    for entry in written.entries:
        if entry.paper_id in grades:
            entry.grade = grades[entry.paper_id]
    return written


def ungraded(retrieval_set: RetrievalSet) -> list[SetEntry]:
    """Returns the entries that still wait for a grade."""
    return [entry for entry in retrieval_set.entries if entry.grade is None]


def grade_counts(retrieval_set: RetrievalSet) -> dict[int | None, int]:
    """Counts each grade, and the Papers with none.

    The table needs this. A recall number without the count of relevant Papers
    gives a reader no denominator.
    """
    counts: dict[int | None, int] = {}
    for entry in retrieval_set.entries:
        counts[entry.grade] = counts.get(entry.grade, 0) + 1
    return counts


def worksheet_rows(retrieval_set: RetrievalSet) -> list[str]:
    """Returns one line for each Paper, in the order the set holds.

    The order is the shuffled order of the file. Nothing here sorts or groups,
    because a grouped list tells the grader which query found the Paper, and
    the rule says to read the title alone.
    """
    rows = []
    for number, entry in enumerate(retrieval_set.entries, start=1):
        grade = "." if entry.grade is None else str(entry.grade)
        rows.append(f"{number:3} {grade}  {entry.paper_id:42} {entry.title}")
    return rows

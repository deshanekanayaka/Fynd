"""The eight reasons one Paper ends with, or without, usable text.

The measurement table in `docs/measurements` counts these, and the count tells
you which step of step 3 to spend a day on. One place holds the strings, so a
table and a result never disagree about a name.
"""

from typing import Final

USABLE: Final = "usable"
NO_DOI: Final = "no_doi"
NO_OPENALEX_RECORD: Final = "no_openalex_record"
NO_REPOSITORY_LOCATION: Final = "no_repository_location"
FETCH_REFUSED: Final = "fetch_refused"
NOT_A_PDF: Final = "not_a_pdf"
TEXT_TOO_SHORT: Final = "text_too_short"
TEXT_NOT_TEXTUAL: Final = "text_not_textual"

# The order the reason table prints, which follows the pipeline from the first
# step to the last.
ALL: Final = (
    USABLE,
    NO_DOI,
    NO_OPENALEX_RECORD,
    NO_REPOSITORY_LOCATION,
    FETCH_REFUSED,
    NOT_A_PDF,
    TEXT_TOO_SHORT,
    TEXT_NOT_TEXTUAL,
)

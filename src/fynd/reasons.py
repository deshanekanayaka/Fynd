"""The reasons one Paper ends with, or without, usable text.

The measurement table in `docs/measurements` counts these, and the count tells
you which step of step 3 to spend a day on. One place holds the strings, so a
table and a result never disagree about a name.
"""

from typing import Final

USABLE: Final = "usable"
NO_DOI: Final = "no_doi"
NO_OPENALEX_RECORD: Final = "no_openalex_record"
# Three reasons replaced `no_repository_location` on 2026-10-11, when an open
# file became a licence question. They are checked in this order, and they tell
# a closed Paper apart from one Fynd refuses to reach. See ADR 0012.
NO_OPEN_LOCATION: Final = "no_open_location"
NO_PDF_LINK: Final = "no_pdf_link"
BLOCKLISTED_ONLY: Final = "blocklisted_only"
# A path robots.txt disallows, which is apart from a 403, because the two say
# different things about a host. See ADR 0012 and RFC 9309.
ROBOTS_REFUSED: Final = "robots_refused"
FETCH_REFUSED: Final = "fetch_refused"
NOT_A_PDF: Final = "not_a_pdf"
TEXT_TOO_SHORT: Final = "text_too_short"
TEXT_NOT_TEXTUAL: Final = "text_not_textual"

# Added on 2026-10-09 with the third usable text check. The reasons above were
# named before the first measurement, which had no check to fail.
NO_SECTION_WORD: Final = "no_section_word"

# The order the reason table prints, which follows the pipeline from the first
# step to the last.
ALL: Final = (
    USABLE,
    NO_DOI,
    NO_OPENALEX_RECORD,
    NO_OPEN_LOCATION,
    NO_PDF_LINK,
    BLOCKLISTED_ONLY,
    ROBOTS_REFUSED,
    FETCH_REFUSED,
    NOT_A_PDF,
    TEXT_TOO_SHORT,
    TEXT_NOT_TEXTUAL,
    NO_SECTION_WORD,
)

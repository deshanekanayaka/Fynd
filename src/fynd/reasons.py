"""Defines shared outcome names for Open copy results and measurement tables.

OpenAlex, the fetcher, and text checks return these strings. The pipeline
keeps one final reason per Paper, and measure.py counts it in the report.
Shared names prevent spelling differences from splitting the same outcome.
"""

from typing import Final

USABLE: Final = "usable"

# Lookup outcomes distinguish missing identifiers, locations, and direct file links.
NO_DOI: Final = "no_doi"
NO_OPENALEX_RECORD: Final = "no_openalex_record"
NO_OPEN_LOCATION: Final = "no_open_location"
NO_PDF_LINK: Final = "no_pdf_link"
BLOCKLISTED_ONLY: Final = "blocklisted_only"

# A robots policy refusal differs from a download rejected with HTTP 403.
ROBOTS_REFUSED: Final = "robots_refused"
FETCH_REFUSED: Final = "fetch_refused"
NOT_A_PDF: Final = "not_a_pdf"

# Separate text failures show whether extraction yielded too little or unusable text.
TEXT_TOO_SHORT: Final = "text_too_short"
TEXT_NOT_TEXTUAL: Final = "text_not_textual"
NO_SECTION_WORD: Final = "no_section_word"

# Print success first, then failures in pipeline order, including zero-count outcomes.
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

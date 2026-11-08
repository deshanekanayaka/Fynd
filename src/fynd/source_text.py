"""Checks extracted Source text before the Open copy pipeline accepts it as usable.

PDF and HTML extraction can produce short error messages or garbled text.
These checks return the first failure reason without changing the text.
Papers also need a section-word match; web pages use only the shared checks.
Passing does not establish truth, relevance, or correct reading order.
"""

from typing import Final

from fynd import reasons

# Reject short extracts such as refusal pages; chosen from the 2026-10-09 measurement.
MIN_CHARACTERS: Final = 3000

# Require at least 95% ordinary characters to limit unrecognised glyphs.
MIN_ORDINARY_SHARE: Final = 0.95

# Accept common punctuation in addition to Unicode letters, digits, and whitespace.
ORDINARY_PUNCTUATION: Final = ".,;:!?'\"()[]{}<>-–—/\\|%&@#£$€+=*^~`_"

# Extracted text can lose heading styles, so match wording rather than layout.
SECTION_WORDS: Final = (
    "abstract",
    "introduction",
    "method",
    "results",
    "discussion",
    "conclusion",
    "references",
)


def is_ordinary(character: str) -> bool:
    """Checks whether a character is alphanumeric, whitespace, or accepted punctuation."""
    if character.isalnum() or character.isspace():
        return True
    return character in ORDINARY_PUNCTUATION


def ordinary_share(text: str) -> float:
    """Returns the fraction of characters accepted by the character check."""
    if not text:
        return 0.0
    ordinary = 0
    for character in text:
        if is_ordinary(character):
            ordinary += 1
    return ordinary / len(text)


def has_a_section_word(text: str) -> bool:
    """Checks for a configured section-word substring, ignoring case."""
    low = text.lower()
    for word in SECTION_WORDS:
        if word in low:
            return True
    return False


def reason_against_text(text: str) -> str:
    """Returns the first shared text-check failure, or an empty string on success."""
    # Check the 3,000-character minimum before calculating the 95% character share.
    if len(text) < MIN_CHARACTERS:
        return reasons.TEXT_TOO_SHORT
    if ordinary_share(text) < MIN_ORDINARY_SHARE:
        return reasons.TEXT_NOT_TEXTUAL
    return ""


def reason_against_paper_text(text: str) -> str:
    """Checks Paper text for length, accepted characters, and a section word."""
    against = reason_against_text(text)
    if against:
        return against
    if not has_a_section_word(text):
        return reasons.NO_SECTION_WORD
    return ""


def reason_against_page_text(text: str) -> str:
    """Checks web-page text for length and accepted characters."""
    # Useful web pages need not use academic section names such as Methods.
    return reason_against_text(text)

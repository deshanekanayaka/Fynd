"""The checks that decide whether a Source text is Usable text.

Usable text is a Source text that passes the checks, so Fynd reads Claims from
it. Every number here comes from the live run of 2026-10-09, which is in
`docs/measurements/open-copy-hosts-2026-10-09.md`.

A Paper and a web page get different checks. A Paper has sections, and a
statistics page has none, so the section word check runs on a Paper only.
"""

from typing import Final

from fynd import reasons

# The 5 Papers that gave Usable text on 2026-10-09 run from 60,363 to 91,205
# characters. The two pages that gave nothing useful are 1,898 and 631
# characters. 3,000 sits between the two groups, far below every real text, and
# it leaves room for a short statistics page at stage 3.
MIN_CHARACTERS: Final = 3000

# The share of characters that must be ordinary. A PDF that extracted badly
# comes back full of control characters and private use glyphs.
# Every real text of the live run scored between 0.9968 and 0.9991, so 0.95
# refuses a text that is one twentieth rubbish and accepts every real one. The
# earlier value of 0.80 was a guess, and it accepted a text one fifth rubbish.
# No file of that run failed this check, so the number has a floor from the
# real texts and no ceiling from a broken one.
MIN_ORDINARY_SHARE: Final = 0.95

# What counts as ordinary beside a letter, a digit, and a space.
ORDINARY_PUNCTUATION: Final = ".,;:!?'\"()[]{}<>-–—/\\|%&@#£$€+=*^~`_"

# One of these words appears in every Paper of the live run. The check asks for
# one word and not for a section heading, because an extractor loses the
# heading style and keeps the word.
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
    """Says whether one character belongs in a readable text."""
    if character.isalnum() or character.isspace():
        return True
    return character in ORDINARY_PUNCTUATION


def ordinary_share(text: str) -> float:
    """Returns the share of characters that belong in a readable text."""
    if not text:
        return 0.0
    # A plain loop over the text. The longest Source text is a few hundred
    # thousand characters, which costs a fraction of one extraction.
    ordinary = 0
    for character in text:
        if is_ordinary(character):
            ordinary += 1
    return ordinary / len(text)


def has_a_section_word(text: str) -> bool:
    """Says whether this text names one of the sections a Paper has."""
    low = text.lower()
    for word in SECTION_WORDS:
        if word in low:
            return True
    return False


def reason_against_text(text: str) -> str:
    """Returns the reason this text is not usable, or an empty string.

    These are the two checks that every Source text passes. An empty answer
    means the text is Usable text so far.
    """
    if len(text) < MIN_CHARACTERS:
        return reasons.TEXT_TOO_SHORT
    if ordinary_share(text) < MIN_ORDINARY_SHARE:
        return reasons.TEXT_NOT_TEXTUAL
    return ""


def reason_against_paper_text(text: str) -> str:
    """Returns the reason this Paper text is not usable, or an empty string.

    A Paper carries the section word check as well. All 5 Papers of the live
    run hold the words method, results and references, and a refusal page or a
    repository landing page holds none of them.
    """
    against = reason_against_text(text)
    if against:
        return against
    if not has_a_section_word(text):
        return reasons.NO_SECTION_WORD
    return ""


def reason_against_page_text(text: str) -> str:
    """Returns the reason this web page text is not usable, or an empty string.

    A web page carries no section word check. The Office for National
    Statistics article of the live run holds the word method, and a gov.uk
    release page holds no section word at all, and neither fact says whether
    the text is usable.
    """
    return reason_against_text(text)
